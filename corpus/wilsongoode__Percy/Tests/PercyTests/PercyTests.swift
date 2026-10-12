import Testing
@testable import Percy
import SwiftData
import Foundation

@Suite(.serialized) final class PercyTests {
    
    private let testStoreDirectory: URL = URL.temporaryDirectory.appending(path: "percy-swift-tests", directoryHint: .isDirectory)
    
    struct ConfigV1Local: PercyConfiguration {
        static var identifier: String { "com.example.percy-swift" }
        static var iCloudContainer: String? { nil }
        static var name: String { "percy-swift-example" }
        static var versionedSchema: any VersionedSchema.Type { TestSchemaV1.self }
        static var migrationPlan: any PercyMigrationPlan.Type { TestForwardMigrationPlan.self }
    }
    
    struct ConfigV2Local: PercyConfiguration {
        static var identifier: String { "com.example.percy-swift" }
        static var iCloudContainer: String? { nil }
        static var name: String { "percy-swift-example" }
        static var versionedSchema: any VersionedSchema.Type { TestSchemaV2.self }
        static var migrationPlan: any PercyMigrationPlan.Type { TestForwardMigrationPlan.self }
    }
    
    struct RollbackConfigV1Local: PercyConfiguration {
        static var identifier: String { "com.example.percy-swift" }
        static var iCloudContainer: String? { nil }
        static var name: String { "percy-swift-example" }
        static var versionedSchema: any VersionedSchema.Type { TestSchemaV1.self }
        static var migrationPlan: any PercyMigrationPlan.Type { TestBackwardMigrationPlan.self }
    }
    
    struct ConfigV3Local: PercyConfiguration {
        static var identifier: String { "com.example.percy-swift" }
        static var iCloudContainer: String? { nil }
        static var name: String { "percy-swift-example" }
        static var versionedSchema: any VersionedSchema.Type { TestSchemaV3.self }
        static var migrationPlan: any PercyMigrationPlan.Type { TestForwardMigrationPlan.self }
    }
    
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
    
    @Test func simpleSetupV1() async throws {
        
        let percyContainer = try await Percy.Container(configuration: ConfigV1Local.self, storeDirectory: testStoreDirectory)
        try await percyContainer.setup()
        let modelContainer = try #require(await percyContainer.container)
        let context = ModelContext(modelContainer)
        
        let person1Name: String = "John Doe"
        let person2Name: String = "Bobby Tables"
        let person2DOB = try #require(Calendar.current.date(from: DateComponents(year: 2000, month: 6, day: 4)))
        let group1Name: String = "Group 1"
        let group2Name: String = "Group 2"
        
        // Create some test data
        let person1 = TestSchemaV1.Person(name: person1Name, dateOfBirth: nil)
        context.insert(person1)
        let person2 = TestSchemaV1.Person(name: person2Name, dateOfBirth: person2DOB)
        context.insert(person2)
        
        // Create some groups
        let group1 = TestSchemaV1.Group(name: group1Name)
        let group2 = TestSchemaV1.Group(name: group2Name)
        context.insert(group1)
        context.insert(group2)
        
        // Assign groups to people
        person1.groups = [group1, group2]
        person2.groups = [group2]
        
        try context.save()
        
        // Try to fetch the data
        let people = try context.fetch(FetchDescriptor<TestSchemaV1.Person>())
        let groups = try context.fetch(FetchDescriptor<TestSchemaV1.Group>())
        
        // Check the data
        #expect(people.count == 2)
        #expect(groups.count == 2)
        
        let johnDoe = try #require(people.first { $0.name == person1Name })
        #expect(johnDoe.dateOfBirth == nil)
        #expect(johnDoe.groups?.count == 2)
        
        let bobbyTables = try #require(people.first { $0.name == person2Name })
        #expect(bobbyTables.dateOfBirth == person2DOB)
        #expect(bobbyTables.groups?.count == 1)
        
        let group1AfterFetch = try #require(groups.first { $0.name == group1Name })
        #expect(group1AfterFetch.name == group1Name)
        #expect(group1AfterFetch.people?.count == 1)
        #expect(group1AfterFetch.people?.contains(where: { $0.name == person1Name }) ?? false)
        
        let group2AfterFetch = try #require(groups.first { $0.name == group2Name })
        #expect(group2AfterFetch.name == group2Name)
        #expect(group2AfterFetch.people?.count == 2)
        #expect(group2AfterFetch.people?.contains(where: { $0.name == person1Name }) ?? false)
        #expect(group2AfterFetch.people?.contains(where: { $0.name == person2Name }) ?? false)
        
        // Clean up
        context.delete(johnDoe)
        context.delete(bobbyTables)
        context.delete(group1AfterFetch)
        context.delete(group2AfterFetch)
        try context.save()
    }
    

    @Test func migrateV1ToV2() async throws {
        
        let person1Name: String = "John Doe"
        let person2Name: String = "Bobby Tables"
        let person2DOB = try #require(Calendar.current.date(from: DateComponents(year: 2000, month: 6, day: 4)))
        let group1Name: String = "Group 1"
        let group2Name: String = "Group 2"
        
        try await {
            let percyContainer = try await Percy.Container(configuration: ConfigV1Local.self, storeDirectory: testStoreDirectory)
            try await percyContainer.setup()
            let modelContainer = try #require(await percyContainer.container)
            let context = ModelContext(modelContainer)
            
            // Create some test data
            let person1 = TestSchemaV1.Person(name: person1Name, dateOfBirth: nil)
            context.insert(person1)
            let person2 = TestSchemaV1.Person(name: person2Name, dateOfBirth: person2DOB)
            context.insert(person2)
            
            // Create some groups
            let group1 = TestSchemaV1.Group(name: group1Name)
            let group2 = TestSchemaV1.Group(name: group2Name)
            context.insert(group1)
            context.insert(group2)
            
            // Assign groups to people
            person1.groups = [group1, group2]
            person2.groups = [group2]
            
            try context.save()
        }()
        
        try await Task.sleep(for: .seconds(1))
        
        try await {
            // Setup V2 container
            let percyContainerV2 = try await Percy.Container(configuration: ConfigV2Local.self, storeDirectory: testStoreDirectory)
            try await percyContainerV2.setup()
            let modelContainerV2 = try #require(await percyContainerV2.container)
            let contextV2 = ModelContext(modelContainerV2)
            
            // Try to fetch the data
            let people = try contextV2.fetch(FetchDescriptor<TestSchemaV2.Person>())
            let groups = try contextV2.fetch(FetchDescriptor<TestSchemaV2.Group>())
            
            // Add new relationship
            let person1V2 = try #require(people.first { $0.name == person1Name })
            let person2V2 = try #require(people.first { $0.name == person2Name })
            person1V2.partner = person2V2
            
            // Check the data
            #expect(people.count == 2)
            #expect(groups.count == 2)
            
            let johnDoe = try #require(people.first { $0.name == person1Name })
            #expect(johnDoe.dateOfBirth == nil)
            #expect(johnDoe.groups?.count == 2)
            
            let bobbyTables = try #require(people.first { $0.name == person2Name })
            #expect(bobbyTables.dateOfBirth == person2DOB)
            #expect(bobbyTables.groups?.count == 1)
            #expect(bobbyTables.partner == johnDoe)
            
            try contextV2.save()
        }()
    }

    
    @Test func rollbackMigrateV2toV1() async throws {
        let person1Name: String = "John Doe"
        let person2Name: String = "Bobby Tables"
        let person2DOB = try #require(Calendar.current.date(from: DateComponents(year: 2000, month: 6, day: 4)))
        let group1Name: String = "Group 1"
        let group2Name: String = "Group 2"
        
        // Setup V1
        try await {
            let percyContainer = try await Percy.Container(configuration: ConfigV1Local.self, storeDirectory: testStoreDirectory)
            try await percyContainer.setup()
            let modelContainer = try #require(await percyContainer.container)
            let context = ModelContext(modelContainer)
            
            // Create some test data
            let person1 = TestSchemaV1.Person(name: person1Name, dateOfBirth: nil)
            context.insert(person1)
            let person2 = TestSchemaV1.Person(name: person2Name, dateOfBirth: person2DOB)
            context.insert(person2)
            
            // Create some groups
            let group1 = TestSchemaV1.Group(name: group1Name)
            let group2 = TestSchemaV1.Group(name: group2Name)
            context.insert(group1)
            context.insert(group2)
            
            // Assign groups to people
            person1.groups = [group1, group2]
            person2.groups = [group2]
            
            try context.save()
        }()
        
        try await Task.sleep(for: .seconds(1))
        
        // Setup V2
        try await {
            // Setup V2 container
            let percyContainerV2 = try await Percy.Container(configuration: ConfigV2Local.self, storeDirectory: testStoreDirectory)
            try await percyContainerV2.setup()
            let modelContainerV2 = try #require(await percyContainerV2.container)
            let contextV2 = ModelContext(modelContainerV2)
            
            // Try to fetch the data
            let people = try contextV2.fetch(FetchDescriptor<TestSchemaV2.Person>())
            let groups = try contextV2.fetch(FetchDescriptor<TestSchemaV2.Group>())
            
            // Add new relationship
            let person1V2 = try #require(people.first { $0.name == person1Name })
            let person2V2 = try #require(people.first { $0.name == person2Name })
            person1V2.partner = person2V2
            
            // Check the data
            #expect(people.count == 2)
            #expect(groups.count == 2)
            
            let johnDoe = try #require(people.first { $0.name == person1Name })
            #expect(johnDoe.dateOfBirth == nil)
            #expect(johnDoe.groups?.count == 2)
            
            let bobbyTables = try #require(people.first { $0.name == person2Name })
            #expect(bobbyTables.dateOfBirth == person2DOB)
            #expect(bobbyTables.groups?.count == 1)
            #expect(bobbyTables.partner == johnDoe)
            
            try contextV2.save()
        }()
        
        try await Task.sleep(for: .seconds(1))
        
        // Reverse migrate from V2 to V1
        try await {
            let percyContainerV1Rollback = try await Percy.Container(configuration: RollbackConfigV1Local.self, storeDirectory: testStoreDirectory)
            try await percyContainerV1Rollback.setup()
            let modelContainerV1Rollback = try #require(await percyContainerV1Rollback.container)
            let contextV1Rollback = ModelContext(modelContainerV1Rollback)
            
            // Try to fetch the data
            let people = try contextV1Rollback.fetch(FetchDescriptor<TestSchemaV1.Person>())
            let groups = try contextV1Rollback.fetch(FetchDescriptor<TestSchemaV1.Group>())
            
            // Check the data
            #expect(people.count == 2)
            #expect(groups.count == 2)
            
            let johnDoe = try #require(people.first { $0.name == person1Name })
            #expect(johnDoe.dateOfBirth == nil)
            #expect(johnDoe.groups?.count == 2)
            
            let bobbyTables = try #require(people.first { $0.name == person2Name })
            #expect(bobbyTables.dateOfBirth == person2DOB)
            #expect(bobbyTables.groups?.count == 1)
            
            try contextV1Rollback.save()
        }()
    }
}
