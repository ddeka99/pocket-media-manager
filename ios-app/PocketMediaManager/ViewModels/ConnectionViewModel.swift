import Foundation

@MainActor
final class ConnectionViewModel: ObservableObject {
    @Published var serverURL: String = ""
    @Published var apiToken: String = ""
    @Published var isValidating = false
    @Published var statusMessage: String?
    @Published var isConnected = false

    func load(from configuration: AppConfiguration) {
        serverURL = configuration.serverURLString
        apiToken = configuration.apiToken
        isConnected = configuration.serverURL != nil && !configuration.apiToken.isEmpty
    }

    func save(into store: AppConfigurationStore) {
        store.configuration = AppConfiguration(serverURLString: serverURL, apiToken: apiToken)
        isConnected = true
    }

    func validate() async {
        isValidating = true
        defer { isValidating = false }

        do {
            let client = APIClient(configuration: AppConfiguration(serverURLString: serverURL, apiToken: apiToken))
            let health = try await client.fetchHealth()
            statusMessage = "Helper reachable. Library count: \(health.libraryCount)"
        } catch {
            statusMessage = error.localizedDescription
        }
    }
}
