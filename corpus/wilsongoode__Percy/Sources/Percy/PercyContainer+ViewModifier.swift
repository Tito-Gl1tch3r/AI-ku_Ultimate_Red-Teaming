import SwiftUI
import SwiftData

public extension View {
    /// Adds Percy persistence to a view hierarchy.
    /// 
    /// Use this modifier to setup Percy and inject the model container:
    /// ```swift
    /// @main
    /// struct YourApp: App {
    ///     var body: some Scene {
    ///         WindowGroup {
    ///             ContentView()
    ///                 .withPercy(configuration: AppStorage.self)
    ///         }
    ///     }
    /// }
    /// ```
    func withPercy<Config: PercyConfiguration>(
        configuration: Config.Type,
        storeURL: URL? = nil
    ) -> some View {
        modifier(PercyViewModifier(configuration: configuration, storeDirectory: storeURL))
    }
}

private struct PercyViewModifier: ViewModifier {
    @State private var percy: Percy.Container
    @State private var setupError: Error?
    
    init<Config: PercyConfiguration>(configuration: Config.Type, storeDirectory: URL? = nil) {
        _percy = State(wrappedValue: try! Percy.Container(configuration: configuration, storeDirectory: storeDirectory))
    }
    
    func body(content: Content) -> some View {
        Group {
            if let container = percy.container {
                content
                    .modelContainer(container)
            } else if let error = setupError {
                ContentUnavailableView(
                    "Database Error",
                    systemImage: "exclamationmark.triangle",
                    description: Text(error.localizedDescription)
                )
            } else {
                ProgressView()
            }
        }
        .task {
            guard percy.container == nil else { return }
            do {
                try await percy.setup()
            } catch {
                setupError = error
            }
        }
    }
}
