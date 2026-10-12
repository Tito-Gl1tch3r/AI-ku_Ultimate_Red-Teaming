#!/usr/bin/env node

// This script directly calls the createTables function
// It will attempt to create the database if it doesn't exist, then create tables

const { Pool } = require('pg');
require('dotenv').config();

async function initDatabase() {
  const password = process.env.POSTGRES_PASSWORD;
  
  // First try to create the database if it doesn't exist
  // Try current user first, then postgres
  const adminConfig = {
    host: process.env.POSTGRES_HOST || 'localhost',
    port: parseInt(process.env.POSTGRES_PORT || '5432'),
    database: 'postgres',
    user: process.env.POSTGRES_USER || process.env.USER || 'postgres',
  };
  if (password) {
    adminConfig.password = password;
  }

  try {
    const adminPool = new Pool(adminConfig);
    console.log('Checking if database exists...');
    const dbCheck = await adminPool.query(
      "SELECT 1 FROM pg_database WHERE datname = 'bugbounty'"
    );
    
    if (dbCheck.rows.length === 0) {
      console.log('Creating database "bugbounty"...');
      await adminPool.query('CREATE DATABASE bugbounty');
      console.log('✓ Database created');
    } else {
      console.log('✓ Database already exists');
    }
    await adminPool.end();
  } catch (error) {
    console.error('Error with database creation:', error.message);
    // Continue anyway - database might already exist
  }

  // Now create tables in the bugbounty database
  const poolConfig = {
    host: process.env.POSTGRES_HOST || 'localhost',
    port: parseInt(process.env.POSTGRES_PORT || '5432'),
    database: 'bugbounty',
    user: process.env.POSTGRES_USER || process.env.USER || 'postgres',
  };
  if (password) {
    poolConfig.password = password;
  }

  const pool = new Pool(poolConfig);
  const client = await pool.connect();
  
  try {
    console.log('Creating tables...');
    
    await client.query(`
      CREATE TABLE IF NOT EXISTS findings (
        id SERIAL PRIMARY KEY,
        target VARCHAR(500) NOT NULL,
        type VARCHAR(100) NOT NULL,
        severity VARCHAR(20) NOT NULL,
        description TEXT NOT NULL,
        payload TEXT,
        response TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        score INTEGER,
        status VARCHAR(20) DEFAULT 'new',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );

      CREATE INDEX IF NOT EXISTS idx_findings_target ON findings(target);
      CREATE INDEX IF NOT EXISTS idx_findings_type ON findings(type);
      CREATE INDEX IF NOT EXISTS idx_findings_severity ON findings(severity);
      CREATE INDEX IF NOT EXISTS idx_findings_timestamp ON findings(timestamp);
    `);

    await client.query(`
      CREATE TABLE IF NOT EXISTS test_results (
        id SERIAL PRIMARY KEY,
        target VARCHAR(500) NOT NULL,
        test_type VARCHAR(100) NOT NULL,
        success BOOLEAN NOT NULL,
        result_data JSONB,
        error_message TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );

      CREATE INDEX IF NOT EXISTS idx_test_results_target ON test_results(target);
      CREATE INDEX IF NOT EXISTS idx_test_results_type ON test_results(test_type);
    `);

    console.log('✓ Tables created successfully');
    console.log('✓ Database initialization complete!');
    console.log('');
    console.log('You can now use the MCP server database features:');
    console.log('  - db.save_finding: Save bug findings');
    console.log('  - db.get_findings: Retrieve findings');
    console.log('  - Test results will be automatically saved');
  } catch (error) {
    console.error('Error creating tables:', error.message);
    if (error.message.includes('password authentication failed')) {
      console.error('');
      console.error('PostgreSQL authentication failed. You need to:');
      console.error('1. Set a password: psql -U postgres -c "ALTER USER postgres PASSWORD \'your_password\';"');
      console.error('2. Update ~/.cursor/mcp.json with POSTGRES_PASSWORD');
    }
    process.exit(1);
  } finally {
    client.release();
    await pool.end();
  }
}

initDatabase().catch((error) => {
  console.error('Fatal error:', error.message);
  process.exit(1);
});

