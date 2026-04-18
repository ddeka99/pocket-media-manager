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
        let configuration = AppConfiguration(serverURLString: serverURL, apiToken: apiToken).normalized
        serverURL = configuration.serverURLString
        apiToken = configuration.apiToken
        store.configuration = configuration
        isConnected = true
    }

    func validate() async {
        isValidating = true
        defer { isValidating = false }

        do {
            let configuration = AppConfiguration(serverURLString: serverURL, apiToken: apiToken).normalized
            serverURL = configuration.serverURLString
            apiToken = configuration.apiToken

            let client = APIClient(configuration: configuration)
            let health = try await client.fetchHealth()
            let summary = try await client.fetchLibrarySummary()
            statusMessage = "Helper reachable. \(summary.totalItems) items indexed, \(summary.directPlayItems) direct-play ready."
            isConnected = health.status == "ok"
        } catch {
            statusMessage = error.localizedDescription
            isConnected = false
        }
    }
}
