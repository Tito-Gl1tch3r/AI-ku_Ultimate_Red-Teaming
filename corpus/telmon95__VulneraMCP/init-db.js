#!/usr/bin/env node

const { Pool } = require('pg');
require('dotenv').config();

async function initDatabase() {
  // First, connect to postgres database to create bugbounty database
  const password = process.env.POSTGRES_PASSWORD;
  const adminConfig = {
    host: process.env.POSTGRES_HOST || 'localhost',
    port: parseInt(process.env.POSTGRES_PORT || '5433'), // PostgreSQL 18 uses port 5433
    database: 'postgres', // Connect to default postgres database
    user: process.env.POSTGRES_USER || 'postgres', // PostgreSQL installer creates 'postgres' superuser
  };
  if (password) {
    adminConfig.password = password;
  }
  const adminPool = new Pool(adminConfig);

  try {
    console.log('Creating database "bugbounty"...');
    await adminPool.query('CREATE DATABASE bugbounty');
    console.log('✓ Database "bugbounty" created');
    await adminPool.end();
  } catch (error) {
    if (error.message.includes('already exists')) {
      console.log('✓ Database "bugbounty" already exists');
      await adminPool.end();
    } else {
      console.error('Error creating database:', error.message);
      await adminPool.end();
      process.exit(1);
    }
  }

  // Now connect to bugbounty database and create tables
  const poolConfig = {
    host: process.env.POSTGRES_HOST || 'localhost',
    port: parseInt(process.env.POSTGRES_PORT || '5433'), // PostgreSQL 18 uses port 5433
    database: 'bugbounty',
    user: process.env.POSTGRES_USER || 'postgres', // PostgreSQL installer creates 'postgres' superuser
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
  } catch (error) {
    console.error('Error creating tables:', error.message);
    process.exit(1);
  } finally {
    client.release();
    await pool.end();
  }
}

initDatabase().catch(console.error);

