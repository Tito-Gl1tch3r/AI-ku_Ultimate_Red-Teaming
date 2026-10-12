//
//  TestSchemaV3.swift
//  Percy
//
//  Created by Wilson Goode on 5/27/25.
//

import Foundation
import SwiftData

enum TestSchemaV3: VersionedSchema {
    static var versionIdentifier: Schema.Version {
        .init(3, 0, 0)
    }
    static var models: [any PersistentModel.Type] {
        [
            TestSchemaV3.Person.self,
            TestSchemaV3.Group.self,
        ]
    }
}

extension TestSchemaV3 {
    @Model
    final class Person {
        var name: String
        var dateOfBirth: Date?
        
        @Relationship var partner: Person?
        
        @Relationship var groups: [Group]?
        
        init(name: String, dateOfBirth: Date? = nil) {
            self.name = name
            self.dateOfBirth = dateOfBirth
        }
    }
    
    @Model
    final class Group {
        var name: String
        var meetingLocation: String?
        
        @Relationship(inverse: \Person.groups) var people: [Person]?
        
        init(name: String) {
            self.name = name
        }
    }
}
