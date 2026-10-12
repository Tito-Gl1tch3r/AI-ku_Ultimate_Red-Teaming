//
//  MigrationStage++.swift
//  Percy
//
//  Created by Wilson Goode on 5/27/25.
//

import SwiftData
import Foundation

extension MigrationStage: @retroactive Comparable {
    public static func < (lhs: MigrationStage, rhs: MigrationStage) -> Bool {
        switch (lhs, rhs) {
        case (.custom(let fromVersion1, _, _, _), .custom(let fromVersion2, _, _, _)):
            return fromVersion1.versionIdentifier < fromVersion2.versionIdentifier
        case (.lightweight(let fromVersion1, _), .lightweight(let fromVersion2, _)):
            return fromVersion1.versionIdentifier < fromVersion2.versionIdentifier
        case (.custom(let fromVersion1, _, _, _), .lightweight(let fromVersion2, _)):
            return fromVersion1.versionIdentifier < fromVersion2.versionIdentifier
        case (.lightweight(let fromVersion1, _), .custom(let fromVersion2, _, _, _)):
            return fromVersion1.versionIdentifier < fromVersion2.versionIdentifier
        default:
            return false
        }
    }
    
    public static func == (lhs: MigrationStage, rhs: MigrationStage) -> Bool {
        switch (lhs, rhs) {
        case (.custom(let fromVersion1, _, _, _), .custom(let fromVersion2, _, _, _)):
            return fromVersion1.versionIdentifier == fromVersion2.versionIdentifier
        case (.lightweight(let fromVersion1, _), .lightweight(let fromVersion2, _)):
            return fromVersion1.versionIdentifier == fromVersion2.versionIdentifier
        case (.custom(let fromVersion1, _, _, _), .lightweight(let fromVersion2, _)):
            return fromVersion1.versionIdentifier == fromVersion2.versionIdentifier
        case (.lightweight(let fromVersion1, _), .custom(let fromVersion2, _, _, _)):
            return fromVersion1.versionIdentifier == fromVersion2.versionIdentifier
        default:
            return false
        }
    }
}
