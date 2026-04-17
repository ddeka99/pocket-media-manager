import AVFoundation
import Foundation

@MainActor
final class PlayerViewModel: ObservableObject {
    @Published var player: AVPlayer?
    @Published var isLoading = false
    @Published var errorMessage: String?

    private var progressTask: Task<Void, Never>?

    deinit {
        progressTask?.cancel()
    }

    func startPlayback(for item: MediaItem, configuration: AppConfiguration) async {
        guard item.compatibleForDirectPlay else {
            errorMessage = item.incompatibleReason ?? "This file cannot be played directly on iPhone in v1."
            return
        }

        isLoading = true
        defer { isLoading = false }

        do {
            let client = APIClient(configuration: configuration)
            let url = try await client.fetchStreamURL(id: item.id)
            let player = AVPlayer(url: url)
            if let resumeTime = item.playback?.positionSeconds, resumeTime > 0 {
                let target = CMTime(seconds: resumeTime, preferredTimescale: 600)
                player.seek(to: target)
            }
            self.player = player
            player.play()
            scheduleProgressUpdates(itemID: item.id, player: player, configuration: configuration)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func scheduleProgressUpdates(itemID: String, player: AVPlayer, configuration: AppConfiguration) {
        progressTask?.cancel()
        progressTask = Task {
            let client = APIClient(configuration: configuration)
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(10))
                let current = player.currentTime().seconds
                guard current.isFinite else { continue }
                let duration = player.currentItem?.duration.seconds
                let safeDuration = duration?.isFinite == true ? duration : nil
                let completed = (safeDuration ?? 0) > 0 && current / (safeDuration ?? 1) > 0.95
                try? await client.updateProgress(
                    id: itemID,
                    payload: ProgressPayload(
                        positionSeconds: current,
                        durationSeconds: safeDuration,
                        completed: completed
                    )
                )
            }
        }
    }
}
