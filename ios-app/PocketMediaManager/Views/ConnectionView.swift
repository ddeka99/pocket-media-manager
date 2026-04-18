import SwiftUI

struct ConnectionView: View {
    enum Mode {
        case onboarding
        case settings

        var title: String {
            switch self {
            case .onboarding:
                return "Connect"
            case .settings:
                return "Settings"
            }
        }

        var headline: String {
            switch self {
            case .onboarding:
                return "Connect your iPhone to the Windows helper."
            case .settings:
                return "Update how this iPhone reaches your helper."
            }
        }

        var subheadline: String {
            switch self {
            case .onboarding:
                return "Enter the LAN URL and pairing token from the PC helper to unlock the library."
            case .settings:
                return "These values stay on-device and can be changed whenever the helper IP or token changes."
            }
        }

        var saveLabel: String {
            switch self {
            case .onboarding:
                return "Save and Continue"
            case .settings:
                return "Save Settings"
            }
        }
    }

    @EnvironmentObject private var configurationStore: AppConfigurationStore
    @Environment(\.dismiss) private var dismiss
    @StateObject private var viewModel = ConnectionViewModel()

    let mode: Mode

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    VStack(alignment: .leading, spacing: 10) {
                        Text(mode.headline)
                            .font(.title2.weight(.bold))
                        Text(mode.subheadline)
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }

                    settingsCard {
                        VStack(alignment: .leading, spacing: 16) {
                            fieldLabel("Helper URL")
                            TextField("http://192.168.x.x:8765", text: $viewModel.serverURL)
                                .textFieldStyle(.roundedBorder)
                                .textInputAutocapitalization(.never)
                                .keyboardType(.URL)
                                .autocorrectionDisabled()

                            fieldLabel("Pairing token")
                            SecureField("Pairing token", text: $viewModel.apiToken)
                                .textFieldStyle(.roundedBorder)
                                .textInputAutocapitalization(.never)
                                .autocorrectionDisabled()
                        }
                    }

                    settingsCard {
                        VStack(spacing: 12) {
                            Button {
                                Task { await viewModel.validate() }
                            } label: {
                                HStack {
                                    if viewModel.isValidating {
                                        ProgressView()
                                            .tint(.accentColor)
                                    } else {
                                        Image(systemName: "antenna.radiowaves.left.and.right")
                                    }
                                    Text("Test Connection")
                                        .fontWeight(.semibold)
                                }
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 14)
                            }
                            .buttonStyle(.bordered)
                            .disabled(viewModel.serverURL.isEmpty || viewModel.apiToken.isEmpty || viewModel.isValidating)

                            Button {
                                viewModel.save(into: configurationStore)
                                if mode == .settings {
                                    dismiss()
                                }
                            } label: {
                                Text(mode.saveLabel)
                                    .fontWeight(.semibold)
                                    .frame(maxWidth: .infinity)
                                    .padding(.vertical, 14)
                            }
                            .buttonStyle(.borderedProminent)
                            .disabled(viewModel.serverURL.isEmpty || viewModel.apiToken.isEmpty)
                        }
                    }

                    if let statusMessage = viewModel.statusMessage {
                        statusCard(message: statusMessage, isConnected: viewModel.isConnected)
                    }
                }
                .padding(.horizontal, 20)
                .padding(.vertical, 20)
            }
            .background(Color(uiColor: .systemGroupedBackground))
            .navigationTitle(mode.title)
            .navigationBarTitleDisplayMode(mode == .settings ? .inline : .large)
            .toolbar {
                if mode == .settings {
                    ToolbarItem(placement: .topBarTrailing) {
                        Button("Done") {
                            dismiss()
                        }
                    }
                }
            }
        }
        .onAppear {
            viewModel.load(from: configurationStore.configuration)
        }
    }

    private func fieldLabel(_ text: String) -> some View {
        Text(text)
            .font(.footnote.weight(.semibold))
            .foregroundStyle(.secondary)
    }

    private func settingsCard<Content: View>(@ViewBuilder content: () -> Content) -> some View {
        content()
            .padding(20)
            .background(
                RoundedRectangle(cornerRadius: 24, style: .continuous)
                    .fill(Color(uiColor: .secondarySystemGroupedBackground))
            )
    }

    private func statusCard(message: String, isConnected: Bool) -> some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: isConnected ? "checkmark.circle.fill" : "exclamationmark.triangle.fill")
                .foregroundStyle(isConnected ? .green : .orange)
                .font(.title3)

            VStack(alignment: .leading, spacing: 4) {
                Text(isConnected ? "Helper Reachable" : "Check Connection")
                    .font(.headline)
                Text(message)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(18)
        .background(
            RoundedRectangle(cornerRadius: 20, style: .continuous)
                .fill(Color(uiColor: .secondarySystemGroupedBackground))
        )
    }
}
