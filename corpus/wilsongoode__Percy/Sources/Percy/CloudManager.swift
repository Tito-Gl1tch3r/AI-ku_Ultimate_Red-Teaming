//
//  CloudManager.swift
//  Percy
//
//  Created by Wilson Goode on 5/4/25.
//

import OSLog
import CloudKit
import SwiftData
import CoreData

actor CloudManager {
    private let logger: Logger
    private let container: CKContainer?
    
    init(
        identifier: String,
        containerIdentifier: String?
    ) {
        self.logger = Logger(subsystem: identifier, category: "Percy.Cloud")
        if let containerIdentifier {
            self.container = CKContainer(identifier: containerIdentifier)
        } else {
            self.container = nil
        }
    }
    
    /// Checks if CloudKit is available
    func checkAvailability() async -> Bool {
        guard let container else {
            logger.debug("No iCloud container configured")
            return false
        }
        do {
            let accountStatus = try await container.accountStatus()
            logger.debug("CloudKit account status: \(String(describing: accountStatus))")
            switch accountStatus {
            case .available, .temporarilyUnavailable:
                return true
            case .noAccount:
                logger.debug("CloudKit unavailable: No iCloud account")
                return false
            case .restricted:
                logger.debug("CloudKit unavailable: Account restricted")
                return false
            case .couldNotDetermine:
                logger.debug("CloudKit unavailable: Could not determine status")
                return false
            @unknown default:
                logger.debug("CloudKit unavailable: Unknown status (\(accountStatus.rawValue))")
                return false
            }
        } catch {
            logger.error("CloudKit availability check failed: \(error)")
            return false
        }
    }
    
    /// Initializes the CloudKit schema for the provided configuration. Only runs in DEBUG mode.
    ///
    /// This function is described in Apple's documentation: [SwiftData: Syncing Model Data Across a Person's Devices](https://developer.apple.com/documentation/swiftdata/syncing-model-data-across-a-persons-devices)
    func initializeSchema(for configuration: any PercyConfiguration.Type, storeURL: URL) async throws {
#if DEBUG
        guard let iCloudContainer = configuration.iCloudContainer else {
            logger.debug("No iCloud container configured")
            return
        }
        // Use an autorelease pool to make sure Swift deallocates the persistent
        // container before setting up the SwiftData stack.
        try autoreleasepool {
            let desc = NSPersistentStoreDescription(url: storeURL)
            let opts = NSPersistentCloudKitContainerOptions(containerIdentifier: iCloudContainer)
            desc.cloudKitContainerOptions = opts
            // Load the store synchronously so it completes before initializing the
            // CloudKit schema.
            desc.shouldAddStoreAsynchronously = false
            if let mom = NSManagedObjectModel.makeManagedObjectModel(for: configuration.versionedSchema.models) {
                let container = NSPersistentCloudKitContainer(name: configuration.name, managedObjectModel: mom)
                container.persistentStoreDescriptions = [desc]
                container.loadPersistentStores {_, err in
                    if let err {
                        print("\(err)")
                        fatalError(err.localizedDescription)
                    }
                }
                // Initialize the CloudKit schema after the store finishes loading.
                try container.initializeCloudKitSchema()
                // Remove and unload the store from the persistent container.
                if let store = container.persistentStoreCoordinator.persistentStores.first {
                    try container.persistentStoreCoordinator.remove(store)
                }
            }
        }
#endif
    }
}
