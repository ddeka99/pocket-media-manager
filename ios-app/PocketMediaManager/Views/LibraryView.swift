import SwiftUI

struct LibraryView: View {
    @EnvironmentObject private var configurationStore: AppConfigurationStore
    @StateObject private var viewModel = LibraryViewModel()

    var body: some View {
        NavigationStack {
            Group {
                if viewModel.isLoading {
                    ProgressView("Loading library...")
                } else if let errorMessage = viewModel.errorMessage {
                    ContentUnavailableView("Could Not Load Library", systemImage: "wifi.exclamationmark", description: Text(errorMessage))
                } else if viewModel.items.isEmpty {
                    ContentUnavailableView("No Media Yet", systemImage: "film", description: Text("Run a library scan on the PC helper after choosing your media folder."))
                } else {
                    List(viewModel.items) { item in
                        NavigationLink(value: item) {
                            MediaRow(item: item)
                        }
                    }
                    .navigationDestination(for: MediaItem.self) { item in
                        MediaDetailView(item: item)
                    }
                }
            }
            .navigationTitle("Library")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Refresh") {
                        Task { await viewModel.load(using: configurationStore.configuration) }
                    }
                }
            }
        }
        .task {
            await viewModel.load(using: configurationStore.configuration)
        }
    }
}
