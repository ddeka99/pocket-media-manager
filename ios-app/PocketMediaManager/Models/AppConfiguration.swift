import Foundation

struct AppConfiguration: Codable, Equatable {
    var serverURLString: String = ""
    var apiToken: String = ""

    var serverURL: URL? {
        let trimmed = serverURLString.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        return URL(string: trimmed)
    }

    var normalized: AppConfiguration {
        AppConfiguration(
            serverURLString: serverURLString.trimmingCharacters(in: .whitespacesAndNewlines),
            apiToken: apiToken.trimmingCharacters(in: .whitespacesAndNewlines)
        )
    }

    static func bootstrapDefault(from bundle: Bundle = .main) -> AppConfiguration? {
        guard let url = bundle.url(forResource: "BootstrapConfiguration", withExtension: "plist"),
              let data = try? Data(contentsOf: url),
              let plist = try? PropertyListSerialization.propertyList(from: data, format: nil),
              let dictionary = plist as? [String: Any]
        else {
            return nil
        }

        guard let serverURLString = dictionary["ServerURL"] as? String,
              let apiToken = dictionary["APIToken"] as? String
        else {
            return nil
        }

        return AppConfiguration(serverURLString: serverURLString, apiToken: apiToken).normalized
    }
}
