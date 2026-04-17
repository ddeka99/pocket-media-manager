import Foundation

enum APIError: LocalizedError {
    case invalidConfiguration
    case invalidResponse
    case server(String)

    var errorDescription: String? {
        switch self {
        case .invalidConfiguration:
            return "Enter a valid server URL and pairing token."
        case .invalidResponse:
            return "The helper returned an unexpected response."
        case .server(let message):
            return message
        }
    }
}

struct ProgressPayload: Encodable {
    let positionSeconds: Double
    let durationSeconds: Double?
    let completed: Bool

    enum CodingKeys: String, CodingKey {
        case positionSeconds = "position_seconds"
        case durationSeconds = "duration_seconds"
        case completed
    }
}

struct FeedbackPayload: Encodable {
    let feedbackType: FeedbackType

    enum CodingKeys: String, CodingKey {
        case feedbackType = "feedback_type"
    }
}

struct APIClient {
    let configuration: AppConfiguration

    private var decoder: JSONDecoder {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return decoder
    }

    private var encoder: JSONEncoder {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        return encoder
    }

    private func makeRequest(path: String, method: String = "GET", body: Data? = nil) throws -> URLRequest {
        guard let baseURL = configuration.serverURL, !configuration.apiToken.isEmpty else {
            throw APIError.invalidConfiguration
        }

        let url = baseURL.appending(path: path)
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("Bearer \(configuration.apiToken)", forHTTPHeaderField: "Authorization")
        if let body {
            request.httpBody = body
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        return request
    }

    func fetchHealth() async throws -> HealthResponse {
        guard let baseURL = configuration.serverURL else {
            throw APIError.invalidConfiguration
        }
        let (data, response) = try await URLSession.shared.data(from: baseURL.appending(path: "health"))
        try validate(response: response, data: data)
        return try decoder.decode(HealthResponse.self, from: data)
    }

    func fetchLibrary() async throws -> [MediaItem] {
        let request = try makeRequest(path: "library")
        let (data, response) = try await URLSession.shared.data(for: request)
        try validate(response: response, data: data)
        return try decoder.decode(MediaListResponse.self, from: data).items
    }

    func fetchMediaItem(id: String) async throws -> MediaItem {
        let request = try makeRequest(path: "library/\(id)")
        let (data, response) = try await URLSession.shared.data(for: request)
        try validate(response: response, data: data)
        return try decoder.decode(MediaItem.self, from: data)
    }

    func fetchStreamURL(id: String) async throws -> URL {
        let request = try makeRequest(path: "library/\(id)/stream", method: "POST")
        let (data, response) = try await URLSession.shared.data(for: request)
        try validate(response: response, data: data)
        return try decoder.decode(StreamResponse.self, from: data).streamURL
    }

    func submitFeedback(id: String, type: FeedbackType) async throws {
        let payload = FeedbackPayload(feedbackType: type)
        let request = try makeRequest(
            path: "library/\(id)/feedback",
            method: "POST",
            body: try encoder.encode(payload)
        )
        let (_, response) = try await URLSession.shared.data(for: request)
        try validate(response: response, data: nil)
    }

    func updateProgress(id: String, payload: ProgressPayload) async throws {
        let request = try makeRequest(
            path: "library/\(id)/progress",
            method: "POST",
            body: try encoder.encode(payload)
        )
        let (_, response) = try await URLSession.shared.data(for: request)
        try validate(response: response, data: nil)
    }

    private func validate(response: URLResponse, data: Data?) throws {
        guard let http = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        guard (200..<300).contains(http.statusCode) else {
            if let data, let message = String(data: data, encoding: .utf8), !message.isEmpty {
                throw APIError.server(message)
            }
            throw APIError.server("Request failed with status code \(http.statusCode).")
        }
    }
}
