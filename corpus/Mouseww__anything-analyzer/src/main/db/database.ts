import Database from 'better-sqlite3'
import { app } from 'electron'
import { join } from 'path'
import { existsSync, mkdirSync } from 'fs'

let db: Database.Database | null = null

/**
 * Get or initialize the SQLite database connection.
 * Database file is stored in the app's user data directory.
 */
export function getDatabase(): Database.Database {
  if (db) return db

  const userDataPath = app.getPath('userData')
  const dbDir = join(userDataPath, 'data')

  if (!existsSync(dbDir)) {
    mkdirSync(dbDir, { recursive: true })
  }

  const dbPath = join(dbDir, 'anything-register.db')

  db = new Database(dbPath)

  // Enable WAL mode for better concurrent read performance
  db.pragma('journal_mode = WAL')
  db.pragma('foreign_keys = ON')

  return db
}

/**
 * Close the database connection (called on app quit).
 */
export function closeDatabase(): void {
  if (db) {
    db.close()
    db = null
  }
}
