import AVFoundation
import Foundation

@MainActor
final class PlayerViewModel: ObservableObject {
    @Published var player: AVPlayer?
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var currentTime: Double = 0
    @Published var duration: Double = 0
    @Published var isPlaying = false

    private var progressTask: Task<Void, Never>?
    private var currentItemID: String?
    private var currentConfiguration: AppConfiguration?
    private var timeObserver: Any?
    private var playbackEndedObserver: NSObjectProtocol?

    deinit {
        progressTask?.cancel()
    }

    func startPlayback(for item: MediaItem, configuration: AppConfiguration) async {
        guard item.compatibleForDirectPlay else {
            errorMessage = item.incompatibleReason ?? "This file cannot be played directly on iPhone in v1."
            return
        }

        stopPlayback()
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            let client = APIClient(configuration: configuration)
            let url = try await client.fetchStreamURL(id: item.id)
            let player = AVPlayer(url: url)
            currentItemID = item.id
            currentConfiguration = configuration
            if let resumeTime = item.playback?.positionSeconds, resumeTime > 0 {
                let target = CMTime(seconds: resumeTime, preferredTimescale: 600)
                _ = await player.seek(to: target)
            }
            self.player = player
            configureObservers(for: player)
            player.play()
            player.rate = 1.0
            isPlaying = true
            scheduleProgressUpdates(itemID: item.id, player: player, configuration: configuration)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func stopPlayback() {
        progressTask?.cancel()
        progressTask = nil
        removeObservers()

        guard let player else {
            currentItemID = nil
            currentConfiguration = nil
            currentTime = 0
            duration = 0
            isPlaying = false
            return
        }

        submitProgressSnapshot(for: player)
        player.pause()
        self.player = nil
        currentItemID = nil
        currentConfiguration = nil
        currentTime = 0
        duration = 0
        isPlaying = false
    }

    func togglePlayback() {
        guard let player else { return }
        if isPlaying {
            player.pause()
            isPlaying = false
        } else {
            player.play()
            player.rate = 1.0
            isPlaying = true
        }
    }

    func seek(by delta: Double) {
        guard player != nil else { return }
        let targetTime = max(0, min(duration > 0 ? duration : .greatestFiniteMagnitude, currentTime + delta))
        seek(to: targetTime)
    }

    func seek(to seconds: Double) {
        guard let player else { return }
        let target = CMTime(seconds: seconds, preferredTimescale: 600)
        Task {
            _ = await player.seek(to: target)
        }
        currentTime = seconds
    }

    private func scheduleProgressUpdates(itemID: String, player: AVPlayer, configuration: AppConfiguration) {
        progressTask?.cancel()
        progressTask = Task {
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(10))
                submitProgressSnapshot(for: player, itemID: itemID, configuration: configuration)
            }
        }
    }

    private func submitProgressSnapshot(for player: AVPlayer, itemID: String? = nil, configuration: AppConfiguration? = nil) {
        let itemID = itemID ?? currentItemID
        let configuration = configuration ?? currentConfiguration
        guard let itemID, let configuration, let payload = progressPayload(for: player) else { return }

        Task {
            try? await APIClient(configuration: configuration).updateProgress(
                id: itemID,
                payload: payload
            )
        }
    }

    private func progressPayload(for player: AVPlayer) -> ProgressPayload? {
        let current = player.currentTime().seconds
        guard current.isFinite else { return nil }
        let duration = player.currentItem?.duration.seconds
        let safeDuration = duration?.isFinite == true ? duration : nil
        let completed = (safeDuration ?? 0) > 0 && current / (safeDuration ?? 1) > 0.95
        return ProgressPayload(
            positionSeconds: current,
            durationSeconds: safeDuration,
            completed: completed
        )
    }

    private func configureObservers(for player: AVPlayer) {
        removeObservers()

        let interval = CMTime(seconds: 0.25, preferredTimescale: 600)
        timeObserver = player.addPeriodicTimeObserver(forInterval: interval, queue: .main) { [weak self, weak player] currentTime in
            guard let self, let player else { return }
            let playerDuration = player.currentItem?.duration.seconds ?? 0
            let resolvedCurrentTime = currentTime.seconds.isFinite ? currentTime.seconds : 0
            let resolvedDuration = playerDuration.isFinite ? playerDuration : 0
            let resolvedIsPlaying = player.rate > 0 || player.timeControlStatus == .playing

            Task { @MainActor in
                self.currentTime = resolvedCurrentTime
                self.duration = resolvedDuration
                self.isPlaying = resolvedIsPlaying
            }
        }

        playbackEndedObserver = NotificationCenter.default.addObserver(
            forName: .AVPlayerItemDidPlayToEndTime,
            object: player.currentItem,
            queue: .main
        ) { [weak self] _ in
            guard let self else { return }
            Task { @MainActor in
                self.isPlaying = false
                self.currentTime = self.duration
            }
        }
    }

    private func removeObservers() {
        if let timeObserver, let player {
            player.removeTimeObserver(timeObserver)
        }
        timeObserver = nil

        if let playbackEndedObserver {
            NotificationCenter.default.removeObserver(playbackEndedObserver)
        }
        playbackEndedObserver = nil
    }
}
