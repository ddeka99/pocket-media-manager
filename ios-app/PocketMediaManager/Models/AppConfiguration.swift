import Foundation

struct AppConfiguration: Codable, Equatable {
    var serverURLString: String = ""
    var apiToken: String = ""

    var serverURL: URL? {
        guard !serverURLString.isEmpty else { return nil }
        return URL(string: serverURLString)
    }
}
