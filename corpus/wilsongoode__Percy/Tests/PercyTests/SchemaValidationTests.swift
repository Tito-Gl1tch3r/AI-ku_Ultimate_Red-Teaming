//
//  SchemaValidationTests.swift
//  Percy
//
//  Created by Wilson Goode on 5/26/25.
//

import Testing
@testable import Percy
import SwiftData
import Foundation

@Suite(.serialized) final class SchemaValidationTests {
    
    private let testStoreDirectory: URL = URL.temporaryDirectory.appending(path: "percy-swift-tests/schema-validation", directoryHint: .isDirectory)
    
    func cleanupDirectory() {
        if FileManager.default.fileExists(atPath: testStoreDirectory.path()) {
            print("Removing directory: \(testStoreDirectory)")
            do {
                try FileManager.default.removeItem(at: testStoreDirectory)
            } catch {
                print("Failed to remove directory: \(error)")
            }
        } else {
            print("Directory does not exist: \(testStoreDirectory)")
        }
    }
    
    init() {
        cleanupDirectory()
    }
    
    deinit {
        cleanupDirectory()
    }
    
    struct FailingConfigSchemaNotInMigration: PercyConfiguration {
        static var identifier: String { "com.example.percy-swift" }
        static var iCloudContainer: String? { nil }
        static var name: String { "percy-swift-example" }
        static var versionedSchema: any VersionedSchema.Type { TestFailingSchemaV1.self }
        static var migrationPlan: any PercyMigrationPlan.Type { TestForwardMigrationPlan.self }
    }
    
    struct FailingConfigSchemaNotValidForCloudKit: PercyConfiguration {
        static var identifier: String { "com.example.percy-swift" }
        static var iCloudContainer: String? { "iCloud.com.example.percy-swift" }
        static var name: String { "percy-swift-example" }
        static var versionedSchema: any VersionedSchema.Type { TestFailingSchemaV1.self }
        static var migrationPlan: any PercyMigrationPlan.Type { TestFailingForwardMigrationPlan.self }
    }

    @Test func schemaNotInMigration() async throws {
        let error = await #expect(throws: PercyError.self) {
            let _ = try await Percy.Container(configuration: FailingConfigSchemaNotInMigration.self, storeDirectory: self.testStoreDirectory)
        }
        #expect(error == .invalidSchema)
    }

    @Test func schemaNotValidForCloudKit() async throws {
        let error = await #expect(throws: PercyError.self) {
            let _ = try await Percy.Container(configuration: FailingConfigSchemaNotValidForCloudKit.self, storeDirectory: self.testStoreDirectory)
        }
        #expect(error == .invalidSchema)
    }

}
