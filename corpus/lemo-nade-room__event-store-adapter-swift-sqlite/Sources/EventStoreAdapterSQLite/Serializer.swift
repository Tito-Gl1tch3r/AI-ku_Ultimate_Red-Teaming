public import EventStoreAdapter
public import Foundation

/// A serializer for converting events to and from binary data.
///
/// This struct provides customizable serialization strategies for domain events,
/// defaulting to JSON encoding but allowing custom implementations for specific needs.
///
/// ## Usage Example
/// ```swift
/// // Using default JSON serialization
/// let serializer = EventSerializer<MyEvent>()
///
/// // Using custom serialization
/// let customSerializer = EventSerializer<MyEvent>(
///   serialize: { event in /* custom logic */ },
///   deserialize: { data in /* custom logic */ }
/// )
/// ```
public struct EventSerializer<Event: EventStoreAdapter.Event>: Sendable {
  /// Converts an event to binary data.
  public var serialize: @Sendable (Event) throws -> Data

  /// Converts binary data back to an event.
  public var deserialize: @Sendable (Data) throws -> Event

  /// Initializes an event serializer with custom or default serialization strategies.
  ///
  /// - Parameters:
  ///   - serialize: A closure that converts events to data. Defaults to JSON encoding.
  ///   - deserialize: A closure that converts data to events. Defaults to JSON decoding.
  public init(
    serialize: @escaping @Sendable (Event) throws -> Data = {
      try serializeForJSON($0, jsonEncoder: .init())
    },
    deserialize: @escaping @Sendable (Data) throws -> Event = {
      try deserializeFromJSON($0, jsonDecoder: .init())
    }
  ) {
    self.serialize = serialize
    self.deserialize = deserialize
  }
}

/// A serializer for converting aggregate snapshots to and from binary data.
///
/// This struct provides customizable serialization strategies for aggregate snapshots,
/// defaulting to JSON encoding but allowing custom implementations for specific needs.
///
/// ## Usage Example
/// ```swift
/// // Using default JSON serialization
/// let serializer = SnapshotSerializer<MyAggregate>()
///
/// // Using custom serialization for better performance
/// let customSerializer = SnapshotSerializer<MyAggregate>(
///   serialize: { aggregate in /* binary format */ },
///   deserialize: { data in /* parse binary */ }
/// )
/// ```
public struct SnapshotSerializer<Aggregate: EventStoreAdapter.Aggregate>: Sendable {
  /// Converts an aggregate snapshot to binary data.
  public var serialize: @Sendable (Aggregate) throws -> Data

  /// Converts binary data back to an aggregate snapshot.
  public var deserialize: @Sendable (Data) throws -> Aggregate

  /// Initializes a snapshot serializer with custom or default serialization strategies.
  ///
  /// - Parameters:
  ///   - serialize: A closure that converts snapshots to data. Defaults to JSON encoding.
  ///   - deserialize: A closure that converts data to snapshots. Defaults to JSON decoding.
  public init(
    serialize: @escaping @Sendable (Aggregate) throws -> Data = {
      try serializeForJSON($0, jsonEncoder: .init())
    },
    deserialize: @escaping @Sendable (Data) throws -> Aggregate = {
      try deserializeFromJSON($0, jsonDecoder: .init())
    }
  ) {
    self.serialize = serialize
    self.deserialize = deserialize
  }
}

/// Serializes a Codable value to JSON data.
///
/// - Parameters:
///   - content: The value to serialize.
///   - jsonEncoder: The JSON encoder to use for serialization.
/// - Returns: The serialized JSON data.
/// - Throws: Encoding errors if serialization fails.
public func serializeForJSON(_ content: some Codable, jsonEncoder: JSONEncoder) throws -> Data {
  try jsonEncoder.encode(content)
}

/// Deserializes JSON data to a Codable value.
///
/// - Parameters:
///   - data: The JSON data to deserialize.
///   - jsonDecoder: The JSON decoder to use for deserialization.
/// - Returns: The deserialized value of type T.
/// - Throws: Decoding errors if deserialization fails.
public func deserializeFromJSON<T: Codable>(_ data: Data, jsonDecoder: JSONDecoder) throws -> T {
  try jsonDecoder.decode(T.self, from: data)
}

/// Errors that can occur during JSON deserialization.
public enum JSONDeserializeError: Error, Sendable {
  /// The provided data is not valid Base64 encoded.
  case notBase64Encoded
}
