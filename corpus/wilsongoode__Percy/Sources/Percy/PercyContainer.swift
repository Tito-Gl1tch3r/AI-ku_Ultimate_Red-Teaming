//
//  PercyContainer.swift
//  Percy
//
//  Created by Wilson Goode on 5/4/25.
//

import SwiftData
import OSLog

public actor Percy {
    
    nonisolated public static let defaultStoreURL: URL = URL.documentsDirectory.appending(path: "PercyStore").appending(path: "percy.store")
    
    /// A container that manages the persistence, backup, cloud sync, and migration of your SwiftData models.
    ///
    /// `Percy.Container` provides a centralized way to manage your app's data persistence needs.
    /// It handles SwiftData model container setup, automatic backups, CloudKit synchronization,
    /// schema migrations, and analytics tracking.
    ///
    /// ## Overview
    /// To use Percy in your app:
    ///
    /// 1. Create a configuration type that conforms to ``PercyConfiguration``:
    /// ```swift
    /// struct AppStorage: PercyConfiguration {
    ///     static let identifier = "com.yourapp.id"
    ///     static let iCloudContainer = "iCloud.com.yourapp.id"
    ///     static let name = "YourApp"
    ///     static let versionedSchema = AppVersionedSchema.self
    ///     static let migrationPlan = AppMigrationPlan.self
    /// }
    /// ```
    ///
    /// 2. To initialize Percy in your app's main entry point, use the ``withPercy`` view modifier:
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
    ///
    /// ## Topics
    ///
    /// ### Configuration
    /// - ``init(configuration:storeURL:)``
    /// - ``container``
    ///
    /// ### Essential Operations
    /// - ``setup(rollback:)``
    ///
    /// ## Notes
    /// - Percy requires iOS 17.0+ or macOS 14.0+
    /// - The container must be set up before use by calling ``setup(rollback:)``
    /// - Automatic backups are created before any potentially destructive operations
    /// - CloudKit sync is automatically enabled when available
    @MainActor @Observable
    public class Container {
        /// The underlying SwiftData model container.
        ///
        /// This property is `nil` until ``setup(rollback:)`` is called successfully.
        public private(set) var container: ModelContainer?
        
        /// The type conforming to ``PercyConfiguration`` that defines your app's storage settings.
        public let configuration: any PercyConfiguration.Type
        private let logger: Logger
        private let storeURL: URL
        private let backup: BackupManager
        private let cloud: CloudManager
        private let migration: MigrationManager
        private let analytics: Analytics
        

        /// Creates a new Percy container with the specified configuration.
        ///
        /// - Parameters:
        ///   - configuration: The type conforming to ``PercyConfiguration`` that defines your app's storage settings.
        ///   - storeDirectory: Optional custom directory for the store file and related files. If not provided, defaults to Documents/PercyStore.
        ///
        /// - Note: After creating the container, you must call ``setup(rollback:)`` before using it.
        public init<Config: PercyConfiguration>(
            configuration: Config.Type,
            storeDirectory: URL? = nil
        ) throws {
            try configuration.validate()
            self.configuration = configuration
            self.logger = Logger(subsystem: configuration.identifier, category: "Percy")
            self.logger.debug("Store directory: \(storeDirectory?.absoluteString ?? "nil")")
            if let storeDirectory, storeDirectory.hasDirectoryPath {
                try? FileManager.default.createDirectory(at: storeDirectory, withIntermediateDirectories: true, attributes: nil)
                self.storeURL = storeDirectory.appending(path: "percy.store")
            } else {
                self.storeURL = Percy.defaultStoreURL
            }
            self.logger.debug("Store URL: \(self.storeURL)")
            // Initialize components
            self.backup = BackupManager(storeURL: self.storeURL, identifier: configuration.identifier)
            self.cloud = CloudManager(identifier: configuration.identifier, containerIdentifier: configuration.iCloudContainer)
            self.migration = MigrationManager(identifier: configuration.identifier)
            self.analytics = Analytics(identifier: configuration.identifier)
        }

        
        /// Sets up the container and prepares it for use.
        ///
        /// This method performs the following operations:
        /// - Creates a backup of existing data
        /// - Checks CloudKit availability
        /// - Sets up the SwiftData model container
        /// - Initializes CloudKit sync if available
        ///
        /// - Parameter rollback: If `true`, rolls back to the last known good state if setup fails.
        ///
        /// - Throws: ``PercyError/setupFailed`` if the setup process fails.
        ///
        /// - Note: This method must be called before using the container.
        public func setup(rollback: Bool = false) async throws {
            do {
                await analytics.trackOperation("setup")
                
                // Create backup before setup
                try await backup.backup()
                
                // Check CloudKit availability
                let cloudAvailable = await cloud.checkAvailability()
                
                // Initialize CloudKit if available
                if cloudAvailable {
                    try await cloud.initializeSchema(for: configuration, storeURL: storeURL)
                }
                
                // Setup container
                let modelContainer = try setupModelContainer(
                    for: configuration.versionedSchema,
                    url: storeURL,
                    enableCloudKit: cloudAvailable,
                    rollback: rollback
                )
                
                self.container = modelContainer
            } catch {
                logger.fault("Failed to setup container: \(error)")
                throw PercyError.setupFailed("\(error)")
            }
        }
        
        /// Sets up and configures the SwiftData model container.
        ///
        /// - Parameters:
        ///   - schema: The schema version to use for the container.
        ///   - url: The URL where the store file should be saved.
        ///   - rollback: If `true`, rolls back to the last known good state if setup fails.
        ///
        /// - Returns: A configured `ModelContainer` instance.
        /// - Throws: ``PercyError/setupFailed`` if the container setup fails.
        private func setupModelContainer(
            for schema: any VersionedSchema.Type,
            url: URL,
            enableCloudKit: Bool = false,
            rollback: Bool
        ) throws -> ModelContainer {
            do {
                logger.debug("Setting up model container for schema v\(schema.versionIdentifier)")
                let modelConfiguration = ModelConfiguration(
                    schema: Schema(versionedSchema: schema),
                    url: url,
                    allowsSave: true,
                    cloudKitDatabase: enableCloudKit ? .automatic : .none
                )
                
                let container = try ModelContainer(
                    for: Schema(versionedSchema: schema),
                    migrationPlan: configuration.migrationPlan,
                    configurations: [modelConfiguration]
                )
                
                logger.debug("Model container setup successfully")
                return container
            } catch {
                logger.error("Failed to setup model container: \(error)")
                
                if rollback {
                    logger.info("Attempting rollback...")
                    // Implement rollback logic here
                    if let nextSchema = configuration.migrationPlan.schemas.last(where: {
                        $0.versionIdentifier < schema.versionIdentifier
                    }) {
                        logger.info("Rolling back to schema v\(nextSchema.versionIdentifier)\(enableCloudKit ? ", without CloudKit" : "")")
                        let container = try setupModelContainer(
                            for: nextSchema,
                            url: url,
                            enableCloudKit: false,
                            rollback: rollback
                        )
                        
                        logger.info("Rollback successful")
                        return container
                    }
                }
                
                throw PercyError.setupFailed("\(error)")
            }
        }
    }
}
