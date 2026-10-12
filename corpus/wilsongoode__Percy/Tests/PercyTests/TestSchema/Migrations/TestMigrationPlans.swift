//
//  TestMigrationPlans.swift
//  Percy
//
//  Created by Wilson Goode on 5/14/25.
//

import SwiftData
import Percy

enum TestForwardMigrationPlan: ForwardMigrationPlan {
    static var schemas: [any VersionedSchema.Type] {
        [
            TestSchemaV1.self,
            TestSchemaV2.self,
            TestSchemaV3.self,
        ]
    }
    
    static var stages: [MigrationStage] {
        [
            migrateV1toV2,
            migrateV2toV3,
        ]
    }
    
    static var migrateV1toV2: MigrationStage {
        .lightweight(
            fromVersion: TestSchemaV1.self,
            toVersion: TestSchemaV2.self
        )
    }
    
    static var migrateV2toV3: MigrationStage {
        .lightweight(
            fromVersion: TestSchemaV2.self,
            toVersion: TestSchemaV3.self
        )
    }
}

// Backward migrations cannot be comingled with forward migrations in a single migration plan
enum TestBackwardMigrationPlan: BackwardMigrationPlan {
    static var schemas: [any VersionedSchema.Type] {
        [
            TestSchemaV1.self,
            TestSchemaV2.self,
            TestSchemaV3.self,
        ]
    }
    
    static var stages: [MigrationStage] {
        [
            rollbackV3toV2,
            rollbackV2toV1,
        ]
    }
    
    // Backward migration stages don't work as MigrationStage.lightweight, so they must be .custom, even if simple
    static var rollbackV2toV1: MigrationStage {
        .custom(
            fromVersion: TestSchemaV2.self,
            toVersion: TestSchemaV1.self,
            willMigrate: nil,
            didMigrate: nil
        )
    }
    
    static var rollbackV3toV2: MigrationStage {
        .custom(
            fromVersion: TestSchemaV3.self,
            toVersion: TestSchemaV2.self,
            willMigrate: nil,
            didMigrate: nil
        )
    }
}

enum TestFailingForwardMigrationPlan: ForwardMigrationPlan {
    static var schemas: [any VersionedSchema.Type] {
        [
            TestFailingSchemaV1.self,
            TestFailingSchemaV2.self,
        ]
    }
    
    static var stages: [MigrationStage] {
        [
            migrateV1toV2,
        ]
    }
    
    static var migrateV1toV2: MigrationStage {
        .lightweight(
            fromVersion: TestFailingSchemaV1.self,
            toVersion: TestFailingSchemaV2.self
        )
    }
}
