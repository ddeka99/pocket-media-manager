import json
import random
import subprocess
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Base directory = the directory this script lives in
BASE_DIR = Path(__file__).resolve().parent

EXCLUDE_FOLDERS = {}
PREFS_FILE = BASE_DIR / "_mpv_prefs.json"

# ----- Tuning knobs -----
UNSEEN_BONUS = 4.0          # exploration weight boost for never-played items
LIKE_BONUS = 1.0           # per-like multiplier contribution
PENDING_BONUS = 0.35       # softer than like
DISLIKE_PENALTY = 0.8      # subtractive penalty per dislike (but not a ban)
MIN_WEIGHT_FLOOR = 0.12    # ensures "n" items still appear sparsely
COOLDOWN_DAYS = 7
COOLDOWN_MULTIPLIER = 0.25
# ------------------------


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def load_prefs():
    if PREFS_FILE.exists():
        try:
            return json.loads(PREFS_FILE.read_text(encoding="utf-8"))
        except Exception:
            # If corrupted, fall back safely
            return {"files": {}}
    return {"files": {}}


def save_prefs(prefs):
    PREFS_FILE.write_text(json.dumps(prefs, indent=2), encoding="utf-8")


def reset_prefs():
    save_prefs({"files": {}})
    print(f"Reset preferences database: {PREFS_FILE}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Pick a weighted random .mp4 file and play it with mpv."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset the preferences database before exiting.",
    )
    parser.add_argument(
        "--select",
        action="store_true",
        help="Choose a folder under the script directory before picking a video.",
    )
    return parser.parse_args()


def list_candidate_folders(base_dir: Path):
    if not base_dir.exists():
        print(f"Base directory not found: {base_dir}")
        return []

    folders = [
        p for p in base_dir.iterdir()
        if p.is_dir() and p.name not in EXCLUDE_FOLDERS
    ]
    folders.sort(key=lambda p: p.name.lower())
    return folders


def choose_folder(folders):
    if not folders:
        print("No eligible folders found.")
        return None

    print("Select a folder:")
    for i, f in enumerate(folders, start=1):
        print(f"  {i}. {f.name}")

    while True:
        choice = input("Enter number: ").strip()
        try:
            idx = int(choice)
            if 1 <= idx <= len(folders):
                return folders[idx - 1]
            print("Number out of range.")
        except ValueError:
            print("Please enter a valid number.")


def find_mp4_files(folder: Path):
    files = []
    for p in folder.rglob("*"):
        if p.is_file() and p.suffix.lower() == ".mp4":
            # Skip anything inside excluded folders (any depth)
            if any(part in EXCLUDE_FOLDERS for part in p.parts):
                continue
            files.append(p)
    return files


def ensure_entries(prefs, files):
    prefs.setdefault("files", {})
    for f in files:
        key = str(f)
        if key not in prefs["files"]:
            prefs["files"][key] = {
                "likes": 0,
                "dislikes": 0,
                "pending": 0,
                "play_count": 0,
                "last_played": None,
                "last_feedback": None,
            }
    # Optionally keep old entries even if file missing
    return prefs


def cooldown_factor(meta):
    lp = meta.get("last_played")
    if not lp:
        return 1.0
    try:
        last_dt = datetime.fromisoformat(lp)
    except ValueError:
        return 1.0

    if datetime.now() - last_dt < timedelta(days=COOLDOWN_DAYS):
        return COOLDOWN_MULTIPLIER
    return 1.0


def compute_weight(meta):
    likes = meta.get("likes", 0)
    dislikes = meta.get("dislikes", 0)
    pending = meta.get("pending", 0)
    play_count = meta.get("play_count", 0)

    # Exploration
    weight = 1.0
    if play_count == 0:
        weight += UNSEEN_BONUS

    # Preference shaping (soft penalty, not exclusion)
    preference = 1.0 + (LIKE_BONUS * likes) + (PENDING_BONUS * pending) - (DISLIKE_PENALTY * dislikes)

    # Clamp so it never becomes too tiny
    preference = max(preference, MIN_WEIGHT_FLOOR)

    weight *= preference
    weight *= cooldown_factor(meta)

    return max(weight, MIN_WEIGHT_FLOOR)


def pick_weighted(files, prefs):
    weights = []
    for f in files:
        meta = prefs["files"].get(str(f), {})
        weights.append(compute_weight(meta))

    # random.choices handles proportional weights
    chosen = random.choices(files, weights=weights, k=1)[0]
    return chosen


def play_with_mpv(file_path: Path):
    cmd = ["mpv", str(file_path)]
    try:
        return subprocess.Popen(cmd)
    except FileNotFoundError:
        print("mpv was not found in PATH.")
        print("Add mpv to PATH or hardcode its path in the script.")
        sys.exit(1)


def record_play(prefs, file_path: Path):
    key = str(file_path)
    meta = prefs["files"][key]
    meta["play_count"] = meta.get("play_count", 0) + 1
    meta["last_played"] = now_iso()


def prompt_feedback():
    val = input("Did you like this recommendation? [y/n/p/enter to skip]: ").strip().lower()
    if val in {"y", "n", "p"}:
        return val
    return None


def apply_feedback(prefs, file_path: Path, fb):
    if not fb:
        return
    key = str(file_path)
    meta = prefs["files"][key]
    if fb == "y":
        meta["likes"] = meta.get("likes", 0) + 1
    elif fb == "n":
        meta["dislikes"] = meta.get("dislikes", 0) + 1
    elif fb == "p":
        meta["pending"] = meta.get("pending", 0) + 1

    meta["last_feedback"] = fb


def main():
    args = parse_args()
    if args.reset:
        reset_prefs()
        return

    scan_dir = BASE_DIR
    if args.select:
        folders = list_candidate_folders(BASE_DIR)
        selected_folder = choose_folder(folders)
        if selected_folder is None:
            return
        scan_dir = selected_folder

    files = find_mp4_files(scan_dir)
    if not files:
        print(f"No .mp4 files found under: {scan_dir}")
        return

    prefs = load_prefs()
    prefs = ensure_entries(prefs, files)

    chosen = pick_weighted(files, prefs)
    print(f"Playing: {chosen}")

    # Update play metadata first
    record_play(prefs, chosen)
    save_prefs(prefs)

    # Start mpv
    proc = play_with_mpv(chosen)

    # Prompt immediately (mpv runs separately)
    fb = prompt_feedback()
    apply_feedback(prefs, chosen, fb)
    save_prefs(prefs)

    # Optional: if you want to wait for mpv to exit, uncomment:
    # proc.wait()


if __name__ == "__main__":
    main()
