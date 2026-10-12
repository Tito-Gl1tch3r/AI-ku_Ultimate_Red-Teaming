//
//  TestFailingSchemaV2.swift
//  Percy
//
//  Created by Wilson Goode on 5/26/25.
//

import Foundation
import SwiftData

enum TestFailingSchemaV2: VersionedSchema {
    static var versionIdentifier: Schema.Version {
        .init(2, 0, 0)
    }
    static var models: [any PersistentModel.Type] {
        [
            TestFailingSchemaV2.Person.self,
            TestFailingSchemaV2.Group.self,
        ]
    }
}

extension TestFailingSchemaV2 {
    @Model
    final class Person {
        @Attribute(.unique)
        var name: String = ""
        var dateOfBirth: Date?
        
        @Relationship var groups: [Group]?
        
        init(name: String, dateOfBirth: Date? = nil) {
            self.name = name
            self.dateOfBirth = dateOfBirth
        }
    }
    
    @Model
    final class Group {
        var name: String = ""
        
        @Relationship(inverse: \Person.groups) var people: [Person]?
        
        init(name: String) {
            self.name = name
        }
    }
}
