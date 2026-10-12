//
//  BackupManager.swift
//  Percy
//
//  Created by Wilson Goode on 5/4/25.
//

import OSLog

actor BackupManager {
    private let storeURL: URL
    private let backupURL: URL
    private let logger: Logger
    
    init(storeURL: URL, identifier: String) {
        self.storeURL = storeURL
        self.backupURL = storeURL.deletingLastPathComponent().appending(path: "percy/backup.store")
        self.logger = Logger(subsystem: identifier, category: "Percy.Backup")
    }
    
    /// Creates a backup of the current store.
    func backup() async throws {
        guard FileManager.default.fileExists(atPath: storeURL.path) else { return }
        
        do {
            try FileManager.default.createDirectory(
                at: backupURL.deletingLastPathComponent(),
                withIntermediateDirectories: true
            )
            
            if FileManager.default.fileExists(atPath: backupURL.path) {
                try FileManager.default.removeItem(at: backupURL)
            }
            
            try FileManager.default.copyItem(at: storeURL, to: backupURL)
            logger.debug("Backup created successfully at \(self.backupURL)")
        } catch {
            logger.error("Backup failed: \(error)")
            throw PercyError.backupFailed("\(error)")
        }
    }
    
    /// Restores the backup to the current store.
    func restore() async throws {
        guard FileManager.default.fileExists(atPath: backupURL.path) else {
            throw PercyError.restoreFailed("No backup found")
        }
        
        do {
            if FileManager.default.fileExists(atPath: storeURL.path) {
                try FileManager.default.removeItem(at: storeURL)
            }
            try FileManager.default.copyItem(at: backupURL, to: storeURL)
            logger.debug("Restore completed successfully")
        } catch {
            logger.error("Restore failed: \(error)")
            throw PercyError.restoreFailed("\(error)")
        }
    }
}
