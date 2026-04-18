import SwiftUI

@main
struct PocketMediaManagerApp: App {
    @UIApplicationDelegateAdaptor(PocketMediaManagerAppDelegate.self) private var appDelegate
    @StateObject private var configurationStore = AppConfigurationStore()
    @StateObject private var orientationController = OrientationController()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(configurationStore)
                .environmentObject(orientationController)
        }
    }
}
