import Dependencies
import EventStoreAdapterSQLite
import FluentSQLiteDriver
import SQLKit
import Testing
import Vapor

@Test
func test() async throws {
  try await withSQLite { sqlite in
    let eventStore = EventStoreForSQLite<Counter.Snapshot, Counter.Event>(on: sqlite)
    let uuid: UUIDGenerator = .incrementing

    // MARK: Create
    do {
      // Arrange
      let now = ISO8601DateFormatter().date(from: "2024-08-24T12:24:36Z")!
      let date: DateGenerator = .constant(now)
      let repository = withDependencies {
        $0.uuid = uuid
        $0.date = date
        $0.eventStore = eventStore
      } operation: {
        Counter.Repository()
      }
      let (counter, event) = Counter.create(uuid: uuid, date: date)

      // Act
      try await repository.persist(event: event, counter: counter)

      // Assert
      let count = await counter.count
      #expect(count == 0)
      let snapshot = try #require(try await eventStore.getLatestSnapshotByAID(aid: counter.aid))
      #expect(
        snapshot
          == .init(
            aid: .init(value: .init(uuidString: "00000000-0000-0000-0000-000000000001")!),
            seqNr: 1,
            version: 1,
            lastUpdatedAt: now,
            count: 0,
          )
      )
      let events = try await eventStore.getEventsByAIDSinceSequenceNumber(aid: counter.aid, seqNr: 1)
      #expect(
        events == [
          .created(
            .init(
              id: .init(uuidString: "00000000-0000-0000-0000-000000000000")!,
              aid: .init(value: .init(uuidString: "00000000-0000-0000-0000-000000000001")!),
              seqNr: 1,
              occurredAt: ISO8601DateFormatter().date(from: "2024-08-24T12:24:36Z")!,
              isCreated: true
            )
          )
        ]
      )
    }

    // MARK: Increment 1
    do {
      // Arrange
      let now = ISO8601DateFormatter().date(from: "2024-08-25T13:00:00Z")!
      let date: DateGenerator = .constant(now)
      let repository = withDependencies {
        $0.uuid = uuid
        $0.date = date
        $0.eventStore = eventStore
      } operation: {
        Counter.Repository()
      }
      let aid = Counter.AID(value: .init(uuidString: "00000000-0000-0000-0000-000000000001")!)
      let counter = try #require(try await repository.find(aid: aid))
      let event = await counter.increment()

      // Act
      try await repository.persist(event: event, version: counter.version)

      // Assert
      let count = await counter.count
      #expect(count == 1)
      let snapshot = try #require(try await eventStore.getLatestSnapshotByAID(aid: counter.aid))
      #expect(
        snapshot
          == .init(
            aid: aid,
            seqNr: 1,
            version: 2,
            lastUpdatedAt: ISO8601DateFormatter().date(from: "2024-08-24T12:24:36Z")!,
            count: 0,
          )
      )
      let events = try await eventStore.getEventsByAIDSinceSequenceNumber(aid: counter.aid, seqNr: 1)
      #expect(
        events == [
          .created(
            .init(
              id: .init(uuidString: "00000000-0000-0000-0000-000000000000")!,
              aid: .init(value: .init(uuidString: "00000000-0000-0000-0000-000000000001")!),
              seqNr: 1,
              occurredAt: ISO8601DateFormatter().date(from: "2024-08-24T12:24:36Z")!,
              isCreated: true
            )
          ),
          .incremented(
            .init(
              id: .init(uuidString: "00000000-0000-0000-0000-000000000002")!,
              aid: aid,
              seqNr: 2,
              occurredAt: ISO8601DateFormatter().date(from: "2024-08-25T13:00:00Z")!,
              isCreated: false,
            )
          ),
        ]
      )
    }

    // MARK: Increment 2
    do {
      // Arrange
      let now = ISO8601DateFormatter().date(from: "2024-08-26T8:01:02Z")!
      let date: DateGenerator = .constant(now)
      let repository = withDependencies {
        $0.uuid = uuid
        $0.date = date
        $0.eventStore = eventStore
      } operation: {
        Counter.Repository()
      }
      let aid = Counter.AID(value: .init(uuidString: "00000000-0000-0000-0000-000000000001")!)
      let counter = try #require(try await repository.find(aid: aid))
      let event = await counter.increment()

      // Act
      try await repository.persist(event: event, version: counter.version)

      // Assert
      let count = await counter.count
      #expect(count == 2)
      let snapshot = try #require(try await eventStore.getLatestSnapshotByAID(aid: counter.aid))
      #expect(
        snapshot
          == .init(
            aid: aid,
            seqNr: 1,
            version: 3,
            lastUpdatedAt: ISO8601DateFormatter().date(from: "2024-08-24T12:24:36Z")!,
            count: 0,
          )
      )
      let events = try await eventStore.getEventsByAIDSinceSequenceNumber(aid: counter.aid, seqNr: 1)
      #expect(
        events == [
          .created(
            .init(
              id: .init(uuidString: "00000000-0000-0000-0000-000000000000")!,
              aid: .init(value: .init(uuidString: "00000000-0000-0000-0000-000000000001")!),
              seqNr: 1,
              occurredAt: ISO8601DateFormatter().date(from: "2024-08-24T12:24:36Z")!,
              isCreated: true
            )
          ),
          .incremented(
            .init(
              id: .init(uuidString: "00000000-0000-0000-0000-000000000002")!,
              aid: aid,
              seqNr: 2,
              occurredAt: ISO8601DateFormatter().date(from: "2024-08-25T13:00:00Z")!,
              isCreated: false,
            )
          ),
          .incremented(
            .init(
              id: .init(uuidString: "00000000-0000-0000-0000-000000000003")!,
              aid: aid,
              seqNr: 3,
              occurredAt: ISO8601DateFormatter().date(from: "2024-08-26T8:01:02Z")!,
              isCreated: false,
            )
          ),
        ]
      )
    }

    // MARK: Increment 3
    do {
      // Arrange
      let now = ISO8601DateFormatter().date(from: "2024-08-26T12:00:00Z")!
      let date: DateGenerator = .constant(now)
      let repository = withDependencies {
        $0.uuid = uuid
        $0.date = date
        $0.eventStore = eventStore
      } operation: {
        Counter.Repository()
      }
      let aid = Counter.AID(value: .init(uuidString: "00000000-0000-0000-0000-000000000001")!)
      let counter = try #require(try await repository.find(aid: aid))
      let event = await counter.increment()

      // Act
      try await repository.persist(event: event, counter: counter)

      // Assert
      let count = await counter.count
      #expect(count == 3)
      let snapshot = try #require(try await eventStore.getLatestSnapshotByAID(aid: counter.aid))
      #expect(
        snapshot
          == .init(
            aid: aid,
            seqNr: 4,
            version: 4,
            lastUpdatedAt: ISO8601DateFormatter().date(from: "2024-08-26T12:00:00Z")!,
            count: 3,
          )
      )
      let events = try await eventStore.getEventsByAIDSinceSequenceNumber(aid: counter.aid, seqNr: 1)
      #expect(
        events == [
          .created(
            .init(
              id: .init(uuidString: "00000000-0000-0000-0000-000000000000")!,
              aid: .init(value: .init(uuidString: "00000000-0000-0000-0000-000000000001")!),
              seqNr: 1,
              occurredAt: ISO8601DateFormatter().date(from: "2024-08-24T12:24:36Z")!,
              isCreated: true
            )
          ),
          .incremented(
            .init(
              id: .init(uuidString: "00000000-0000-0000-0000-000000000002")!,
              aid: aid,
              seqNr: 2,
              occurredAt: ISO8601DateFormatter().date(from: "2024-08-25T13:00:00Z")!,
              isCreated: false,
            )
          ),
          .incremented(
            .init(
              id: .init(uuidString: "00000000-0000-0000-0000-000000000003")!,
              aid: aid,
              seqNr: 3,
              occurredAt: ISO8601DateFormatter().date(from: "2024-08-26T8:01:02Z")!,
              isCreated: false,
            )
          ),
          .incremented(
            .init(
              id: .init(uuidString: "00000000-0000-0000-0000-000000000004")!,
              aid: aid,
              seqNr: 4,
              occurredAt: ISO8601DateFormatter().date(from: "2024-08-26T12:00:00Z")!,
              isCreated: false,
            )
          ),
        ]
      )
    }

    // MARK: Decrement 1
    do {
      // Arrange
      let now = ISO8601DateFormatter().date(from: "2024-08-27T00:00:00Z")!
      let date: DateGenerator = .constant(now)
      let repository = withDependencies {
        $0.uuid = uuid
        $0.date = date
        $0.eventStore = eventStore
      } operation: {
        Counter.Repository()
      }
      let aid = Counter.AID(value: .init(uuidString: "00000000-0000-0000-0000-000000000001")!)
      let counter = try #require(try await repository.find(aid: aid))
      let event = await counter.decrement()

      // Act
      try await repository.persist(event: event, version: counter.version)

      // Assert
      let count = await counter.count
      #expect(count == 2)
      let snapshot = try #require(try await eventStore.getLatestSnapshotByAID(aid: counter.aid))
      #expect(
        snapshot
          == .init(
            aid: aid,
            seqNr: 4,
            version: 5,
            lastUpdatedAt: ISO8601DateFormatter().date(from: "2024-08-26T12:00:00Z")!,
            count: 3,
          )
      )
      let events = try await eventStore.getEventsByAIDSinceSequenceNumber(aid: counter.aid, seqNr: 1)
      #expect(
        events == [
          .created(
            .init(
              id: .init(uuidString: "00000000-0000-0000-0000-000000000000")!,
              aid: .init(value: .init(uuidString: "00000000-0000-0000-0000-000000000001")!),
              seqNr: 1,
              occurredAt: ISO8601DateFormatter().date(from: "2024-08-24T12:24:36Z")!,
              isCreated: true
            )
          ),
          .incremented(
            .init(
              id: .init(uuidString: "00000000-0000-0000-0000-000000000002")!,
              aid: aid,
              seqNr: 2,
              occurredAt: ISO8601DateFormatter().date(from: "2024-08-25T13:00:00Z")!,
              isCreated: false,
            )
          ),
          .incremented(
            .init(
              id: .init(uuidString: "00000000-0000-0000-0000-000000000003")!,
              aid: aid,
              seqNr: 3,
              occurredAt: ISO8601DateFormatter().date(from: "2024-08-26T8:01:02Z")!,
              isCreated: false,
            )
          ),
          .incremented(
            .init(
              id: .init(uuidString: "00000000-0000-0000-0000-000000000004")!,
              aid: aid,
              seqNr: 4,
              occurredAt: ISO8601DateFormatter().date(from: "2024-08-26T12:00:00Z")!,
              isCreated: false,
            )
          ),
          .decremented(
            .init(
              id: .init(uuidString: "00000000-0000-0000-0000-000000000005")!,
              aid: aid,
              seqNr: 5,
              occurredAt: ISO8601DateFormatter().date(from: "2024-08-27T00:00:00Z")!,
              isCreated: false,
            )
          ),
        ]
      )
    }
  }
}

extension EventStoreForSQLite<Counter.Snapshot, Counter.Event>: Counter.EventStore {}

func withSQLite(action: (any SQLDatabase) async throws -> Void) async throws {
  var env = try Environment.detect()
  try LoggingSystem.bootstrap(from: &env)

  let app = try await Application.make(env)

  app.databases.use(.sqlite(.memory), as: .sqlite)
  app.migrations.add(SnapshotMigration())
  app.migrations.add(JournalMigration())

  try await app.autoMigrate()

  let sqlite = app.db as! (any SQLDatabase)

  do {
    try await action(sqlite)
  }
  catch {
    try await app.asyncShutdown()
    throw error
  }
  try await app.asyncShutdown()
}
