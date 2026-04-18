import SwiftUI

struct RootView: View {
    @EnvironmentObject private var configurationStore: AppConfigurationStore

    var body: some View {
        if configurationStore.configuration.serverURL == nil || configurationStore.configuration.apiToken.isEmpty {
            ConnectionView(mode: .onboarding)
        } else {
            LibraryView()
        }
    }
}
