import Foundation

@MainActor
final class LibraryViewModel: ObservableObject {
    @Published var items: [MediaItem] = []
    @Published var isLoading = false
    @Published var errorMessage: String?

    func load(using configuration: AppConfiguration) async {
        isLoading = true
        defer { isLoading = false }

        do {
            let client = APIClient(configuration: configuration)
            items = try await client.fetchLibrary()
            errorMessage = nil
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
