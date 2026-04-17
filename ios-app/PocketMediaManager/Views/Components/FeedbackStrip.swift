import SwiftUI

struct FeedbackStrip: View {
    let item: MediaItem
    let onTap: (FeedbackType) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Feedback")
                .font(.headline)
            HStack {
                ForEach(FeedbackType.allCases) { feedback in
                    Button(feedback.label) { onTap(feedback) }
                        .buttonStyle(.bordered)
                        .tint(item.feedback.contains(feedback) ? .accentColor : .gray)
                }
            }
        }
    }
}
