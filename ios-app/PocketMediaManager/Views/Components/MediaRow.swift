import SwiftUI

struct MediaRow: View {
    let item: MediaItem

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(item.title)
                    .font(.headline)
                Spacer()
                if let playback = item.playback, playback.completed {
                    Text("Watched")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.green)
                }
            }

            Text(item.folder.isEmpty ? item.fileName : "\(item.folder) / \(item.fileName)")
                .font(.footnote)
                .foregroundStyle(.secondary)

            if let playback = item.playback, let duration = playback.durationSeconds, duration > 0 {
                ProgressView(value: playback.positionSeconds, total: duration)
            }

            if !item.compatibleForDirectPlay {
                Text(item.incompatibleReason ?? "Not available for direct play")
                    .font(.caption)
                    .foregroundStyle(.orange)
            }
        }
        .padding(.vertical, 4)
    }
}
