import Foundation

@MainActor
final class AppConfigurationStore: ObservableObject {
    @Published var configuration: AppConfiguration {
        didSet { persist() }
    }

    private let defaultsKey = "PocketMediaManager.configuration"

    init() {
        if let data = UserDefaults.standard.data(forKey: defaultsKey),
           let decoded = try? JSONDecoder().decode(AppConfiguration.self, from: data) {
            configuration = decoded
        } else {
            configuration = AppConfiguration()
        }
    }

    private func persist() {
        guard let encoded = try? JSONEncoder().encode(configuration) else { return }
        UserDefaults.standard.set(encoded, forKey: defaultsKey)
    }
}
