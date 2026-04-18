import SwiftUI

struct MediaRow: View {
    let item: MediaItem

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .top, spacing: 12) {
                ZStack {
                    RoundedRectangle(cornerRadius: 14, style: .continuous)
                        .fill(Color.blue.opacity(item.compatibleForDirectPlay ? 0.14 : 0.08))
                    Image(systemName: item.compatibleForDirectPlay ? "play.rectangle.fill" : "film.fill")
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(item.compatibleForDirectPlay ? .blue : .secondary)
                }
                .frame(width: 44, height: 44)

                VStack(alignment: .leading, spacing: 8) {
                    HStack(alignment: .firstTextBaseline) {
                        Text(item.title)
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(.primary)
                            .lineLimit(2)
                        Spacer(minLength: 10)
                        Image(systemName: "chevron.right")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.tertiary)
                    }

                    Text(item.folder.isEmpty ? item.fileName : "\(item.folder) / \(item.fileName)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)

                    HStack(spacing: 8) {
                        if let playback = item.playback, playback.completed {
                            badge(text: "Watched", tint: .green)
                        } else if let resumeText = resumeSummary {
                            badge(text: "Resume \(resumeText)", tint: .indigo)
                        }

                        if !item.compatibleForDirectPlay {
                            badge(text: "Needs conversion", tint: .orange)
                        }
                    }
                }
            }

            if let playback = item.playback, let duration = playback.durationSeconds, duration > 0 {
                VStack(alignment: .leading, spacing: 6) {
                    ProgressView(value: playback.positionSeconds, total: duration)
                        .tint(.blue)
                    Text(progressLabel(playback: playback, duration: duration))
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 12)
        .background(
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .fill(Color(uiColor: .secondarySystemGroupedBackground))
        )
    }

    private var resumeSummary: String? {
        guard let playback = item.playback, !playback.completed, playback.positionSeconds > 0 else { return nil }
        return format(seconds: playback.positionSeconds)
    }

    private func badge(text: String, tint: Color) -> some View {
        Text(text)
            .font(.caption2.weight(.semibold))
            .foregroundStyle(tint)
            .padding(.horizontal, 8)
            .padding(.vertical, 5)
            .background(
                Capsule(style: .continuous)
                    .fill(tint.opacity(0.12))
            )
    }

    private func progressLabel(playback: PlaybackProgress, duration: Double) -> String {
        let current = format(seconds: playback.positionSeconds)
        let total = format(seconds: duration)
        return "\(current) of \(total)"
    }

    private func format(seconds: Double) -> String {
        let formatter = DateComponentsFormatter()
        formatter.allowedUnits = seconds >= 3600 ? [.hour, .minute, .second] : [.minute, .second]
        formatter.zeroFormattingBehavior = [.pad]
        return formatter.string(from: seconds) ?? "--:--"
    }
}
