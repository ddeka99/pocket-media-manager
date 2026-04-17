import AVKit
import SwiftUI

struct MediaDetailView: View {
    @EnvironmentObject private var configurationStore: AppConfigurationStore
    @StateObject private var playerViewModel = PlayerViewModel()

    let item: MediaItem

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                VStack(alignment: .leading, spacing: 8) {
                    Text(item.title)
                        .font(.title2.weight(.semibold))
                    Text(item.relativePath)
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }

                if let player = playerViewModel.player {
                    VideoPlayer(player: player)
                        .frame(height: 240)
                        .clipShape(RoundedRectangle(cornerRadius: 16))
                }

                Button(item.compatibleForDirectPlay ? "Play" : "Unavailable on iPhone") {
                    Task { await playerViewModel.startPlayback(for: item, configuration: configurationStore.configuration) }
                }
                .buttonStyle(.borderedProminent)
                .disabled(!item.compatibleForDirectPlay || playerViewModel.isLoading)

                FeedbackStrip(item: item) { feedback in
                    Task {
                        try? await APIClient(configuration: configurationStore.configuration).submitFeedback(id: item.id, type: feedback)
                    }
                }

                Group {
                    metadataRow(label: "Folder", value: item.folder.isEmpty ? "Root" : item.folder)
                    metadataRow(label: "Container", value: item.container ?? "Unknown")
                    metadataRow(label: "Video", value: item.videoCodec ?? "Unknown")
                    metadataRow(label: "Audio", value: item.audioCodec ?? "Unknown")
                    metadataRow(label: "Duration", value: item.durationSeconds.map { format(seconds: $0) } ?? "Unknown")
                    metadataRow(label: "Resume", value: item.playback.map { format(seconds: $0.positionSeconds) } ?? "Not started")
                }

                if let errorMessage = playerViewModel.errorMessage {
                    Text(errorMessage)
                        .font(.footnote)
                        .foregroundStyle(.red)
                }
            }
            .padding()
        }
        .navigationTitle("Details")
        .navigationBarTitleDisplayMode(.inline)
    }

    private func metadataRow(label: String, value: String) -> some View {
        HStack {
            Text(label)
                .foregroundStyle(.secondary)
            Spacer()
            Text(value)
        }
        .font(.subheadline)
    }

    private func format(seconds: Double) -> String {
        let formatter = DateComponentsFormatter()
        formatter.allowedUnits = seconds >= 3600 ? [.hour, .minute, .second] : [.minute, .second]
        formatter.zeroFormattingBehavior = [.pad]
        return formatter.string(from: seconds) ?? "--:--"
    }
}
