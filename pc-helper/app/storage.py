from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import RuntimeConfig
from .models import FeedbackType, FolderSummary, LibraryScanJob, LibrarySummaryResponse, MediaItem, PlaybackProgress


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self, config: RuntimeConfig) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS app_config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS media_items (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    relative_path TEXT NOT NULL UNIQUE,
                    absolute_path TEXT NOT NULL,
                    folder TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    duration_seconds REAL,
                    video_codec TEXT,
                    audio_codec TEXT,
                    width INTEGER,
                    height INTEGER,
                    container TEXT,
                    compatible_for_direct_play INTEGER NOT NULL,
                    incompatible_reason TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS playback_state (
                    media_item_id TEXT PRIMARY KEY,
                    position_seconds REAL NOT NULL,
                    duration_seconds REAL,
                    completed INTEGER NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(media_item_id) REFERENCES media_items(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS playback_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    media_item_id TEXT NOT NULL,
                    position_seconds REAL NOT NULL,
                    duration_seconds REAL,
                    completed INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(media_item_id) REFERENCES media_items(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS feedback_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    media_item_id TEXT NOT NULL,
                    feedback_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(media_item_id) REFERENCES media_items(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS scan_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    status TEXT NOT NULL,
                    scanned_files INTEGER NOT NULL DEFAULT 0,
                    started_at TEXT NOT NULL,
                    completed_at TEXT
                );
                """
            )
            self.upsert_config(conn, config)

    def upsert_config(self, conn: sqlite3.Connection, config: RuntimeConfig) -> None:
        values = {
            "api_token": config.api_token,
            "media_root": str(config.media_root) if config.media_root else "",
        }
        conn.executemany(
            """
            INSERT INTO app_config(key, value) VALUES(?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            list(values.items()),
        )

    def load_config(self) -> RuntimeConfig:
        with self.connect() as conn:
            rows = conn.execute("SELECT key, value FROM app_config").fetchall()
        values = {row["key"]: row["value"] for row in rows}
        media_root = Path(values["media_root"]) if values.get("media_root") else None
        return RuntimeConfig(media_root=media_root, api_token=values["api_token"])

    def update_media_root(self, media_root: Path) -> RuntimeConfig:
        config = self.load_config()
        config.media_root = media_root
        with self.connect() as conn:
            self.upsert_config(conn, config)
        return config

    def create_scan_job(self) -> int:
        with self.connect() as conn:
            cursor = conn.execute(
                "INSERT INTO scan_jobs(status, scanned_files, started_at) VALUES(?, ?, ?)",
                ("running", 0, utcnow_iso()),
            )
            return int(cursor.lastrowid)

    def finish_scan_job(self, job_id: int, scanned_files: int) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE scan_jobs
                SET status = ?, scanned_files = ?, completed_at = ?
                WHERE id = ?
                """,
                ("completed", scanned_files, utcnow_iso(), job_id),
            )

    def latest_scan_job(self) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM scan_jobs ORDER BY id DESC LIMIT 1"
            ).fetchone()

    def replace_media_index(self, records: list[dict[str, Any]]) -> None:
        with self.connect() as conn:
            conn.executemany(
                """
                INSERT INTO media_items(
                    id, title, file_name, relative_path, absolute_path, folder, size_bytes,
                    duration_seconds, video_codec, audio_codec, width, height, container,
                    compatible_for_direct_play, incompatible_reason, updated_at
                )
                VALUES(
                    :id, :title, :file_name, :relative_path, :absolute_path, :folder, :size_bytes,
                    :duration_seconds, :video_codec, :audio_codec, :width, :height, :container,
                    :compatible_for_direct_play, :incompatible_reason, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    file_name = excluded.file_name,
                    relative_path = excluded.relative_path,
                    absolute_path = excluded.absolute_path,
                    folder = excluded.folder,
                    size_bytes = excluded.size_bytes,
                    duration_seconds = excluded.duration_seconds,
                    video_codec = excluded.video_codec,
                    audio_codec = excluded.audio_codec,
                    width = excluded.width,
                    height = excluded.height,
                    container = excluded.container,
                    compatible_for_direct_play = excluded.compatible_for_direct_play,
                    incompatible_reason = excluded.incompatible_reason,
                    updated_at = excluded.updated_at
                """,
                records,
            )
            keep_ids = [record["id"] for record in records]
            if keep_ids:
                placeholders = ",".join("?" for _ in keep_ids)
                conn.execute(
                    f"DELETE FROM media_items WHERE id NOT IN ({placeholders})",
                    keep_ids,
                )
            else:
                conn.execute("DELETE FROM media_items")

    def list_media_items(self) -> list[MediaItem]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    m.*,
                    p.position_seconds,
                    p.duration_seconds AS progress_duration_seconds,
                    p.completed,
                    p.updated_at AS progress_updated_at
                FROM media_items m
                LEFT JOIN playback_state p ON p.media_item_id = m.id
                ORDER BY lower(m.folder), lower(m.title)
                """
            ).fetchall()
            feedback_rows = conn.execute(
                """
                SELECT media_item_id, feedback_type
                FROM feedback_events
                WHERE id IN (
                    SELECT MAX(id)
                    FROM feedback_events
                    GROUP BY media_item_id, feedback_type
                )
                """
            ).fetchall()

        feedback_map: dict[str, list[FeedbackType]] = {}
        for row in feedback_rows:
            feedback_map.setdefault(row["media_item_id"], []).append(
                FeedbackType(row["feedback_type"])
            )

        return [self._row_to_media_item(row, feedback_map.get(row["id"], [])) for row in rows]

    def get_media_item(self, media_item_id: str) -> MediaItem | None:
        items = [item for item in self.list_media_items() if item.id == media_item_id]
        return items[0] if items else None

    def absolute_path_for_item(self, media_item_id: str) -> Path | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT absolute_path FROM media_items WHERE id = ?",
                (media_item_id,),
            ).fetchone()
        if not row:
            return None
        return Path(row["absolute_path"])

    def save_progress(
        self,
        media_item_id: str,
        position_seconds: float,
        duration_seconds: float | None,
        completed: bool,
    ) -> PlaybackProgress:
        timestamp = utcnow_iso()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO playback_events(media_item_id, position_seconds, duration_seconds, completed, created_at)
                VALUES(?, ?, ?, ?, ?)
                """,
                (media_item_id, position_seconds, duration_seconds, int(completed), timestamp),
            )
            conn.execute(
                """
                INSERT INTO playback_state(media_item_id, position_seconds, duration_seconds, completed, updated_at)
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(media_item_id) DO UPDATE SET
                    position_seconds = excluded.position_seconds,
                    duration_seconds = excluded.duration_seconds,
                    completed = excluded.completed,
                    updated_at = excluded.updated_at
                """,
                (media_item_id, position_seconds, duration_seconds, int(completed), timestamp),
            )
        return PlaybackProgress(
            media_item_id=media_item_id,
            position_seconds=position_seconds,
            duration_seconds=duration_seconds,
            completed=completed,
            updated_at=datetime.fromisoformat(timestamp),
        )

    def add_feedback(self, media_item_id: str, feedback_type: FeedbackType) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO feedback_events(media_item_id, feedback_type, created_at)
                VALUES(?, ?, ?)
                """,
                (media_item_id, feedback_type.value, utcnow_iso()),
            )

    def count_media_items(self) -> int:
        with self.connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS count FROM media_items").fetchone()
        return int(row["count"])

    def library_summary(self) -> LibrarySummaryResponse:
        config = self.load_config()
        with self.connect() as conn:
            counts = conn.execute(
                """
                SELECT
                    COUNT(*) AS total_items,
                    SUM(CASE WHEN compatible_for_direct_play = 1 THEN 1 ELSE 0 END) AS direct_play_items,
                    SUM(CASE WHEN compatible_for_direct_play = 0 THEN 1 ELSE 0 END) AS incompatible_items
                FROM media_items
                """
            ).fetchone()
            folder_rows = conn.execute(
                """
                SELECT
                    CASE
                        WHEN folder = '' THEN 'Root'
                        ELSE folder
                    END AS folder,
                    COUNT(*) AS item_count
                FROM media_items
                GROUP BY folder
                ORDER BY item_count DESC, lower(folder)
                LIMIT 5
                """
            ).fetchall()
            latest_scan_row = conn.execute(
                "SELECT * FROM scan_jobs ORDER BY id DESC LIMIT 1"
            ).fetchone()

        latest_scan = (
            LibraryScanJob.model_validate(dict(latest_scan_row))
            if latest_scan_row is not None
            else None
        )
        return LibrarySummaryResponse(
            media_root=str(config.media_root) if config.media_root else None,
            total_items=int(counts["total_items"] or 0),
            direct_play_items=int(counts["direct_play_items"] or 0),
            incompatible_items=int(counts["incompatible_items"] or 0),
            latest_scan=latest_scan,
            top_folders=[
                FolderSummary(folder=row["folder"], item_count=int(row["item_count"]))
                for row in folder_rows
            ],
        )

    def _row_to_media_item(
        self, row: sqlite3.Row, feedback_types: list[FeedbackType]
    ) -> MediaItem:
        playback = None
        if row["position_seconds"] is not None:
            playback = PlaybackProgress(
                media_item_id=row["id"],
                position_seconds=row["position_seconds"],
                duration_seconds=row["progress_duration_seconds"],
                completed=bool(row["completed"]),
                updated_at=(
                    datetime.fromisoformat(row["progress_updated_at"])
                    if row["progress_updated_at"]
                    else None
                ),
            )
        return MediaItem(
            id=row["id"],
            title=row["title"],
            file_name=row["file_name"],
            relative_path=row["relative_path"],
            folder=row["folder"],
            size_bytes=row["size_bytes"],
            duration_seconds=row["duration_seconds"],
            video_codec=row["video_codec"],
            audio_codec=row["audio_codec"],
            width=row["width"],
            height=row["height"],
            container=row["container"],
            compatible_for_direct_play=bool(row["compatible_for_direct_play"]),
            incompatible_reason=row["incompatible_reason"],
            updated_at=datetime.fromisoformat(row["updated_at"]),
            playback=playback,
            feedback=feedback_types,
        )
