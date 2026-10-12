public import Fluent
import Foundation
import SQLKit

/// A database migration that creates the journals table for event sourcing.
///
/// This migration sets up the schema for storing domain events in an append-only journal,
/// which forms the primary source of truth in the event sourcing pattern.
///
/// ## Table Structure
/// The journal table uses a composite primary key of (`aid`, `seq_nr`) to ensure
/// each event has a unique position within its aggregate's event stream.
public struct JournalMigration: AsyncMigration {
  /// The name of the database schema/table for storing journal events.
  public var schema: String

  /// Initializes a new journal migration with the specified schema name.
  ///
  /// - Parameter schema: The name of the database table for journal events. Defaults to "journals".
  public init(schema: String = defaultJournalTableName) {
    self.schema = schema
  }

  /// Creates the journals table in the database.
  ///
  /// The table includes columns for:
  /// - `aid`: Aggregate identifier
  /// - `seq_nr`: Event sequence number within the aggregate
  /// - `payload`: Serialized event data
  /// - `occurred_at`: Timestamp when the event occurred
  ///
  /// The composite primary key consists of `aid` and `seq_nr` to ensure
  /// each event has a unique position in the aggregate's event stream.
  ///
  /// - Parameter database: The database connection to run the migration on.
  /// - Throws: Database errors if the migration fails.
  public func prepare(on database: any Database) async throws {
    guard let sql = database as? (any SQLDatabase) else {
      fatalError("")
    }
    try await sql.create(table: schema)
      .column("aid", type: .text, .notNull)
      .column("seq_nr", type: .int, .notNull)
      .column("payload", type: .blob, .notNull)
      .column("occurred_at", type: .bigint, .notNull)
      .primaryKey("aid", "seq_nr")
      .ifNotExists()
      .run()
  }

  /// Drops the journals table from the database.
  ///
  /// - Parameter database: The database connection to run the reversion on.
  /// - Throws: Database errors if the reversion fails.
  public func revert(on database: any Database) async throws {
    try await database.schema(schema).delete()
  }
}
