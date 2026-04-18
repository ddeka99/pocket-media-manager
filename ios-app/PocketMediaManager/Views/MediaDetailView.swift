import SwiftUI

struct MediaDetailView: View {
    @EnvironmentObject private var configurationStore: AppConfigurationStore
    @EnvironmentObject private var orientationController: OrientationController
    @StateObject private var playerViewModel = PlayerViewModel()
    @State private var isPresentingPlayer = false

    let item: MediaItem

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                headerBlock
                playbackBlock
                feedbackCard
                technicalDetailsCard

                if let errorMessage = playerViewModel.errorMessage {
                    statusCard(
                        title: "Playback issue",
                        systemImage: "exclamationmark.triangle.fill",
                        message: errorMessage,
                        tint: .orange
                    )
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
        }
        .background(Color(uiColor: .systemGroupedBackground))
        .navigationTitle(item.title)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar(.visible, for: .navigationBar)
        .fullScreenCover(isPresented: $isPresentingPlayer, onDismiss: {
            orientationController.restorePortrait()
            playerViewModel.stopPlayback()
        }) {
            FullScreenPlayerView(playerViewModel: playerViewModel)
            .environmentObject(orientationController)
        }
    }

    private var headerBlock: some View {
        VStack(alignment: .leading, spacing: 16) {
            VStack(alignment: .leading, spacing: 8) {
                Text(item.title)
                    .font(.title2.weight(.bold))
                Text(item.relativePath)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            HStack(spacing: 12) {
                if let playback = item.playback, playback.completed {
                    heroBadge(systemImage: "checkmark.circle.fill", text: "Watched", tint: .green)
                } else if let resumeText = resumeSummary {
                    heroBadge(systemImage: "clock.arrow.circlepath", text: resumeText, tint: .indigo)
                }

                if !item.compatibleForDirectPlay {
                    heroBadge(systemImage: "exclamationmark.triangle.fill", text: "Needs another format", tint: .orange)
                }
            }
        }
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .fill(Color(uiColor: .secondarySystemGroupedBackground))
        )
    }

    private var playbackBlock: some View {
        VStack(alignment: .leading, spacing: 16) {
            Button {
                Task {
                    await playerViewModel.startPlayback(for: item, configuration: configurationStore.configuration)
                    if playerViewModel.player != nil {
                        orientationController.activateLandscapePlayback()
                        isPresentingPlayer = true
                    }
                }
            } label: {
                HStack {
                    if playerViewModel.isLoading {
                        ProgressView()
                            .tint(.white)
                    } else {
                        Image(systemName: "play.fill")
                    }
                    Text(item.compatibleForDirectPlay ? "Play" : "Unavailable on iPhone")
                        .fontWeight(.semibold)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 14)
            }
            .buttonStyle(.borderedProminent)
            .disabled(!item.compatibleForDirectPlay || playerViewModel.isLoading)

            HStack(spacing: 12) {
                playbackStat(title: "Duration", value: item.durationSeconds.map { format(seconds: $0) } ?? "Unknown")
                playbackStat(title: "Resume", value: resumeSummary ?? "Not started")
            }

            if !item.compatibleForDirectPlay {
                Text(item.incompatibleReason ?? "This file cannot be played directly on iPhone in v1.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .fill(Color(uiColor: .secondarySystemGroupedBackground))
        )
    }

    private var feedbackCard: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Feedback")
                .font(.subheadline.weight(.semibold))

            FeedbackStrip(item: item) { feedback in
                Task {
                    try? await APIClient(configuration: configurationStore.configuration).submitFeedback(id: item.id, type: feedback)
                }
            }
        }
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .fill(Color(uiColor: .secondarySystemGroupedBackground))
        )
    }

    private var technicalDetailsCard: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Technical Details")
                .font(.subheadline.weight(.semibold))

            VStack(spacing: 12) {
                metadataRow(label: "Folder", value: item.folder.isEmpty ? "Root" : item.folder)
                metadataRow(label: "Container", value: item.container ?? "Unknown")
                metadataRow(label: "Video", value: item.videoCodec ?? "Unknown")
                metadataRow(label: "Audio", value: item.audioCodec ?? "Unknown")
                metadataRow(label: "Resolution", value: resolutionText)
                metadataRow(label: "Updated", value: item.updatedAt.formatted(date: .abbreviated, time: .shortened))
            }
        }
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .fill(Color(uiColor: .secondarySystemGroupedBackground))
        )
    }

    private func heroBadge(systemImage: String, text: String, tint: Color) -> some View {
        Label(text, systemImage: systemImage)
            .font(.caption2.weight(.semibold))
            .foregroundStyle(tint)
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(
                Capsule(style: .continuous)
                    .fill(tint.opacity(0.12))
            )
    }

    private func playbackStat(title: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(.caption2)
                .foregroundStyle(.secondary)
            Text(value)
                .font(.caption.weight(.semibold))
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .fill(Color(uiColor: .tertiarySystemGroupedBackground))
        )
    }

    private func statusCard(title: String, systemImage: String, message: String, tint: Color) -> some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: systemImage)
                .foregroundStyle(tint)
                .font(.title3)

            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.subheadline.weight(.semibold))
                Text(message)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(14)
        .background(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .fill(Color(uiColor: .secondarySystemGroupedBackground))
        )
    }

    private func metadataRow(label: String, value: String) -> some View {
        HStack(alignment: .firstTextBaseline) {
            Text(label)
                .foregroundStyle(.secondary)
            Spacer(minLength: 20)
            Text(value)
                .multilineTextAlignment(.trailing)
        }
        .font(.caption)
    }

    private var resumeSummary: String? {
        guard let playback = item.playback else { return nil }
        if playback.completed {
            return "Watched"
        }
        guard playback.positionSeconds > 0 else { return nil }
        return format(seconds: playback.positionSeconds)
    }

    private var resolutionText: String {
        guard let width = item.width, let height = item.height else { return "Unknown" }
        return "\(width)×\(height)"
    }

    private func format(seconds: Double) -> String {
        let formatter = DateComponentsFormatter()
        formatter.allowedUnits = seconds >= 3600 ? [.hour, .minute, .second] : [.minute, .second]
        formatter.zeroFormattingBehavior = [.pad]
        return formatter.string(from: seconds) ?? "--:--"
    }
}
