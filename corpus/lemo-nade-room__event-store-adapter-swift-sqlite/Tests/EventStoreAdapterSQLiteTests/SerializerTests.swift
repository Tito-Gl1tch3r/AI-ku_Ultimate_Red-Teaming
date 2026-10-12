import EventStoreAdapter
import EventStoreAdapterSQLite
import Foundation
import Testing

@Suite
struct SerializerTests {
  @Test
  func event() throws {
    // Arrange
    let sut = EventSerializer<Counter.Event>()

    let event = Counter.Event.incremented(
      .init(
        id: UUID(uuidString: "00000000-0000-0000-0000-000000000000")!,
        aid: .init(value: UUID(uuidString: "00000000-0000-0000-0000-000000000001")!),
        seqNr: 1,
        occurredAt: ISO8601DateFormatter().date(from: "2024-01-24T12:34:56Z")!,
        isCreated: false
      )
    )

    let serialized = try sut.serialize(event)

    // Act
    let deserialized = try sut.deserialize(serialized)

    // Assert
    #expect(deserialized == event)
  }

  @Test
  func snapshot() throws {
    // Arrange
    let sut = SnapshotSerializer<Counter.Snapshot>()

    let snapshot = Counter.Snapshot(
      aid: .init(value: UUID(uuidString: "00000000-0000-0000-0000-000000000000")!),
      seqNr: 2,
      version: 2,
      lastUpdatedAt: ISO8601DateFormatter().date(from: "2024-01-24T12:34:56Z")!,
      count: 3
    )
    let serialized = try sut.serialize(snapshot)

    // Act
    let deserialized = try sut.deserialize(serialized)

    // Assert
    #expect(deserialized == snapshot)
  }
}
