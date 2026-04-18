import Foundation

enum FeedbackType: String, Codable, CaseIterable, Identifiable {
    case liked
    case disliked
    case saveForLater = "save_for_later"

    var id: String { rawValue }

    var label: String {
        switch self {
        case .liked: return "Liked"
        case .disliked: return "Disliked"
        case .saveForLater: return "Save for Later"
        }
    }
}

struct MediaListResponse: Codable {
    let items: [MediaItem]
}

struct MediaItem: Codable, Identifiable, Hashable {
    let id: String
    let title: String
    let fileName: String
    let relativePath: String
    let folder: String
    let sizeBytes: Int
    let durationSeconds: Double?
    let videoCodec: String?
    let audioCodec: String?
    let width: Int?
    let height: Int?
    let container: String?
    let compatibleForDirectPlay: Bool
    let incompatibleReason: String?
    let updatedAt: Date
    let playback: PlaybackProgress?
    let feedback: [FeedbackType]

    enum CodingKeys: String, CodingKey {
        case id
        case title
        case fileName = "file_name"
        case relativePath = "relative_path"
        case folder
        case sizeBytes = "size_bytes"
        case durationSeconds = "duration_seconds"
        case videoCodec = "video_codec"
        case audioCodec = "audio_codec"
        case width
        case height
        case container
        case compatibleForDirectPlay = "compatible_for_direct_play"
        case incompatibleReason = "incompatible_reason"
        case updatedAt = "updated_at"
        case playback
        case feedback
    }
}

struct PlaybackProgress: Codable, Hashable {
    let mediaItemId: String
    let positionSeconds: Double
    let durationSeconds: Double?
    let completed: Bool
    let updatedAt: Date?

    enum CodingKeys: String, CodingKey {
        case mediaItemId = "media_item_id"
        case positionSeconds = "position_seconds"
        case durationSeconds = "duration_seconds"
        case completed
        case updatedAt = "updated_at"
    }
}

struct StreamResponse: Codable {
    let streamURL: URL

    enum CodingKeys: String, CodingKey {
        case streamURL = "stream_url"
    }
}

struct HealthResponse: Codable {
    let status: String
    let appName: String
    let apiVersion: String
    let mediaRootConfigured: Bool
    let libraryCount: Int

    enum CodingKeys: String, CodingKey {
        case status
        case appName = "app_name"
        case apiVersion = "api_version"
        case mediaRootConfigured = "media_root_configured"
        case libraryCount = "library_count"
    }
}

struct LibrarySummaryResponse: Codable {
    let mediaRoot: String?
    let totalItems: Int
    let directPlayItems: Int
    let incompatibleItems: Int

    enum CodingKeys: String, CodingKey {
        case mediaRoot = "media_root"
        case totalItems = "total_items"
        case directPlayItems = "direct_play_items"
        case incompatibleItems = "incompatible_items"
    }
}
