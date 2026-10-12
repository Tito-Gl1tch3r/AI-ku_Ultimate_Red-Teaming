public import Fluent
import Foundation
import SQLKit

/// A database migration that creates the snapshots table for event sourcing.
///
/// This migration sets up the schema for storing aggregate snapshots,
/// which are periodic state captures of aggregates to optimize event replay performance.
///
/// ## Purpose
/// Snapshots reduce the number of events that need to be replayed when rebuilding
/// aggregate state, significantly improving performance for aggregates with long event histories.
public struct SnapshotMigration: AsyncMigration {
  /// The name of the database schema/table for storing snapshots.
  public var schema: String

  /// Initializes a new snapshot migration with the specified schema name.
  ///
  /// - Parameter schema: The name of the database table for snapshots. Defaults to "snapshots".
  public init(schema: String = defaultSnapshotTableName) {
    self.schema = schema
  }

  /// Creates the snapshots table in the database.
  ///
  /// The table includes columns for:
  /// - `aid`: Aggregate identifier (primary key)
  /// - `payload`: Serialized aggregate state data
  /// - `seq_nr`: Sequence number of the last applied event
  /// - `version`: Schema version of the serialized data
  /// - `last_updated_at`: Timestamp of the last update
  ///
  /// - Parameter database: The database connection to run the migration on.
  /// - Throws: Database errors if the migration fails.
  public func prepare(on database: any Database) async throws {
    try await database.schema(schema)
      .field("aid", .string, .required, .identifier(auto: false))
      .field("payload", .data, .required)
      .field("seq_nr", .uint64, .required)
      .field("version", .uint64, .required)
      .field("last_updated_at", .uint64, .required)
      .create()
  }

  /// Drops the snapshots table from the database.
  ///
  /// - Parameter database: The database connection to run the reversion on.
  /// - Throws: Database errors if the reversion fails.
  public func revert(on database: any Database) async throws {
    try await database.schema(schema).delete()
  }
}
