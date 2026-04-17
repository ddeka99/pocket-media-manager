import SwiftUI

struct ConnectionView: View {
    @EnvironmentObject private var configurationStore: AppConfigurationStore
    @StateObject private var viewModel = ConnectionViewModel()

    var body: some View {
        NavigationStack {
            Form {
                Section("Helper Connection") {
                    TextField("http://192.168.x.x:8765", text: $viewModel.serverURL)
                        .textInputAutocapitalization(.never)
                        .keyboardType(.URL)
                        .autocorrectionDisabled()

                    SecureField("Pairing token", text: $viewModel.apiToken)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                }

                Section {
                    Button("Test Connection") {
                        Task { await viewModel.validate() }
                    }
                    .disabled(viewModel.serverURL.isEmpty || viewModel.apiToken.isEmpty || viewModel.isValidating)

                    Button("Save and Continue") {
                        viewModel.save(into: configurationStore)
                    }
                    .disabled(viewModel.serverURL.isEmpty || viewModel.apiToken.isEmpty)
                }

                if let statusMessage = viewModel.statusMessage {
                    Section("Status") {
                        Text(statusMessage)
                            .font(.footnote)
                    }
                }
            }
            .navigationTitle("Connect")
        }
        .onAppear {
            viewModel.load(from: configurationStore.configuration)
        }
    }
}
