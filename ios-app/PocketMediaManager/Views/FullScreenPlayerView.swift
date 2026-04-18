import AVKit
import SwiftUI

struct FullScreenPlayerView: View {
    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject private var orientationController: OrientationController
    @ObservedObject var playerViewModel: PlayerViewModel

    var body: some View {
        ZStack(alignment: .topLeading) {
            Color.black.ignoresSafeArea()

            if let player = playerViewModel.player {
                SystemPlayerView(player: player)
                    .ignoresSafeArea()
            } else {
                ProgressView()
                    .tint(.white)
            }

            Button {
                dismiss()
            } label: {
                Image(systemName: "xmark")
                    .font(.footnote.weight(.bold))
                    .foregroundStyle(.white)
                    .frame(width: 30, height: 30)
                    .background(Color.black.opacity(0.35), in: Circle())
            }
            .padding(.leading, 16)
            .padding(.top, 12)
        }
        .statusBarHidden()
        .onAppear {
            orientationController.activateLandscapePlayback()
        }
        .onDisappear {
            orientationController.restorePortrait()
        }
    }
}

private struct SystemPlayerView: UIViewControllerRepresentable {
    let player: AVPlayer

    func makeUIViewController(context: Context) -> AVPlayerViewController {
        let controller = AVPlayerViewController()
        controller.player = player
        controller.showsPlaybackControls = true
        controller.videoGravity = .resizeAspect
        controller.allowsPictureInPicturePlayback = true
        controller.updatesNowPlayingInfoCenter = true
        return controller
    }

    func updateUIViewController(_ controller: AVPlayerViewController, context: Context) {
        controller.player = player
    }
}
