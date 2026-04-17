import SwiftUI

@main
struct PocketMediaManagerApp: App {
    @StateObject private var configurationStore = AppConfigurationStore()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(configurationStore)
        }
    }
}
