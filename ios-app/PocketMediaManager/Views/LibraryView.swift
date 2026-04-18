import SwiftUI

struct LibraryView: View {
    @EnvironmentObject private var configurationStore: AppConfigurationStore
    @StateObject private var viewModel = LibraryViewModel()
    @State private var isPresentingSettings = false

    var body: some View {
        NavigationStack {
            ZStack {
                Color(uiColor: .systemGroupedBackground)
                    .ignoresSafeArea()

                ScrollView {
                    VStack(alignment: .leading, spacing: 14) {
                        if viewModel.isLoading && viewModel.items.isEmpty {
                            loadingState
                        } else if let errorMessage = viewModel.errorMessage, viewModel.items.isEmpty {
                            messageCard(
                                title: "Could Not Load Library",
                                systemImage: "wifi.exclamationmark",
                                message: errorMessage
                            )
                        } else if viewModel.items.isEmpty {
                            messageCard(
                                title: "No Media Yet",
                                systemImage: "film",
                                message: "Run a library scan on the PC helper after choosing your media folder."
                            )
                        } else {
                            LazyVStack(spacing: 10) {
                                ForEach(viewModel.items) { item in
                                    NavigationLink(value: item) {
                                        MediaRow(item: item)
                                    }
                                    .buttonStyle(.plain)
                                }
                            }
                        }

                        if let errorMessage = viewModel.errorMessage, !viewModel.items.isEmpty {
                            inlineNotice(text: errorMessage, isError: true)
                        }
                    }
                    .padding(.horizontal, 16)
                    .padding(.top, 10)
                    .padding(.bottom, 20)
                }
                .refreshable {
                    await viewModel.load(using: configurationStore.configuration)
                }
            }
            .safeAreaInset(edge: .top, spacing: 0) {
                libraryHeader
            }
            .navigationDestination(for: MediaItem.self) { item in
                MediaDetailView(item: item)
            }
            .toolbar(.hidden, for: .navigationBar)
            .sheet(isPresented: $isPresentingSettings) {
                ConnectionView(mode: .settings)
            }
        }
        .task {
            await viewModel.load(using: configurationStore.configuration)
        }
    }

    private var libraryHeader: some View {
        ZStack {
            Text("Library")
                .font(.headline.weight(.semibold))

            HStack {
                headerButton(systemImage: "slider.horizontal.3") {
                    isPresentingSettings = true
                }
                .accessibilityLabel("Open Settings")

                Spacer()

                headerButton(systemImage: viewModel.isLoading ? nil : "arrow.clockwise") {
                    Task { await viewModel.load(using: configurationStore.configuration) }
                } progress: {
                    ProgressView()
                        .controlSize(.small)
                        .tint(.primary)
                }
                .disabled(viewModel.isLoading)
            }
        }
        .padding(.horizontal, 16)
        .padding(.top, 6)
        .padding(.bottom, 8)
        .background(Color(uiColor: .systemGroupedBackground))
    }

    private var loadingState: some View {
        HStack(spacing: 12) {
            ProgressView()
            VStack(alignment: .leading, spacing: 2) {
                Text("Loading library…")
                    .font(.subheadline.weight(.semibold))
                Text("Refreshing your indexed media.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .background(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .fill(Color(uiColor: .secondarySystemGroupedBackground))
        )
    }

    private func messageCard(title: String, systemImage: String, message: String) -> some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: systemImage)
                .font(.title3)
                .foregroundStyle(.secondary)
            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.subheadline.weight(.semibold))
                Text(message)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .background(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .fill(Color(uiColor: .secondarySystemGroupedBackground))
        )
    }

    private func inlineNotice(text: String, isError: Bool) -> some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: isError ? "exclamationmark.triangle.fill" : "checkmark.circle.fill")
                .foregroundStyle(isError ? .orange : .green)
            Text(text)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .fill(Color(uiColor: .secondarySystemGroupedBackground))
        )
    }

    private func headerButton<Progress: View>(
        systemImage: String?,
        action: @escaping () -> Void,
        @ViewBuilder progress: () -> Progress = { EmptyView() }
    ) -> some View {
        Button(action: action) {
            Group {
                if let systemImage {
                    Image(systemName: systemImage)
                        .font(.headline.weight(.semibold))
                } else {
                    progress()
                }
            }
            .frame(width: 34, height: 34)
            .background(
                Circle()
                    .fill(Color(uiColor: .secondarySystemGroupedBackground))
            )
        }
        .buttonStyle(.plain)
    }
}
