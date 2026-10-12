//
//  VersionedSchema++.swift
//  Percy
//
//  Created by Wilson Goode on 5/21/25.
//

import SwiftData
import Foundation
import OSLog

extension VersionedSchema {
    static func versionString() -> String {
        "\(self) v\(versionIdentifier.major).\(versionIdentifier.minor).\(versionIdentifier.patch)"
    }
}

extension VersionedSchema {
    static func validateForCloudKit(_ logger: Logger) -> Bool {
        let schema = Schema(versionedSchema: self)
        var validationErrors: [CloudKitModelValidationError] = []
        schema.entities.forEach { entity in
            entity.attributes.forEach { attribute in
                let attributeText = "\(entity.name).\(attribute.name)"
                if attribute.isUnique {
                    validationErrors.append(.uniqueConstraintNotAllowed(attributeText))
                }
                if !attribute.isOptional && (attribute.defaultValue == nil) {
                    validationErrors.append(.nonOptionalAttributeWithoutDefault(attributeText))
                }
            }
            entity.relationships.forEach { relationship in
                let relationshipText = "\(entity.name).\(relationship.name)"
                if !relationship.isOptional {
                    validationErrors.append(.nonOptionalRelationship(relationshipText))
                }
                if relationship.inverseKeyPath == nil {
                    validationErrors.append(.missingInverseRelationship(relationshipText))
                }
                if relationship.deleteRule == .deny {
                    validationErrors.append(.denyDeletionRuleUsed(relationshipText))
                }
//                if relationship {
//                    validationErrors.append(.orderedRelationshipUsed(relationshipText))
//                }
            }
        }
        
        if !validationErrors.isEmpty {
            logger.error("Validation errors: \(validationErrors)")
            return false
        }
        
        return true
    }
}

enum CloudKitModelValidationError: LocalizedError {
    case uniqueConstraintNotAllowed(String)
    case nonOptionalAttributeWithoutDefault(String)
    case nonOptionalRelationship(String)
    case missingInverseRelationship(String)
    case denyDeletionRuleUsed(String)
    case orderedRelationshipUsed(String)
    
    var errorDescription: String? {
        switch self {
        case .uniqueConstraintNotAllowed(let detail):
            return "Unique constraints are not allowed for CloudKit sync: \(detail)"
        case .nonOptionalAttributeWithoutDefault(let detail):
            return "Non-optional attributes must have default values: \(detail)"
        case .nonOptionalRelationship(let detail):
            return "Relationships must be optional: \(detail)"
        case .missingInverseRelationship(let detail):
            return "All relationships must have inverse relationships: \(detail)"
        case .denyDeletionRuleUsed(let detail):
            return "Deny deletion rule is not allowed: \(detail)"
        case .orderedRelationshipUsed(let detail):
            return "Ordered relationships are not allowed: \(detail)"
        }
    }
}
