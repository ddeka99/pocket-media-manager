import SwiftUI

struct RootView: View {
    @EnvironmentObject private var configurationStore: AppConfigurationStore

    var body: some View {
        if configurationStore.configuration.serverURL == nil || configurationStore.configuration.apiToken.isEmpty {
            ConnectionView()
        } else {
            TabView {
                LibraryView()
                    .tabItem {
                        Label("Library", systemImage: "film.stack")
                    }

                ConnectionView()
                    .tabItem {
                        Label("Settings", systemImage: "gearshape")
                    }
            }
        }
    }
}
