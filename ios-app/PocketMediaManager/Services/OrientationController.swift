import SwiftUI
import UIKit

final class PocketMediaManagerAppDelegate: NSObject, UIApplicationDelegate {
    static var orientationLock: UIInterfaceOrientationMask = .portrait

    func application(
        _ application: UIApplication,
        supportedInterfaceOrientationsFor window: UIWindow?
    ) -> UIInterfaceOrientationMask {
        Self.orientationLock
    }
}

@MainActor
final class OrientationController: ObservableObject {
    func activateLandscapePlayback() {
        setOrientation(mask: .landscapeRight, interfaceOrientation: .landscapeRight)
    }

    func restorePortrait() {
        setOrientation(mask: .portrait, interfaceOrientation: .portrait)
    }

    private func setOrientation(
        mask: UIInterfaceOrientationMask,
        interfaceOrientation: UIInterfaceOrientation
    ) {
        PocketMediaManagerAppDelegate.orientationLock = mask

        guard let scene = UIApplication.shared.connectedScenes
            .compactMap({ $0 as? UIWindowScene })
            .first
        else { return }

        scene.requestGeometryUpdate(.iOS(interfaceOrientations: mask)) { _ in }

        UIDevice.current.setValue(interfaceOrientation.rawValue, forKey: "orientation")
        scene.windows.first?.rootViewController?.setNeedsUpdateOfSupportedInterfaceOrientations()
    }
}
