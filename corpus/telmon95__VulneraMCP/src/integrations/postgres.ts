import { Pool, PoolClient, QueryResult } from 'pg';
import { Finding } from '../types';

let pool: Pool | null = null;

export function initPostgres(): Pool {
  if (pool) return pool;

  pool = new Pool({
    host: process.env.POSTGRES_HOST || 'localhost',
    port: parseInt(process.env.POSTGRES_PORT || '5433'), // PostgreSQL 18 uses port 5433
    database: process.env.POSTGRES_DB || 'bugbounty',
    user: process.env.POSTGRES_USER || 'postgres', // PostgreSQL installer creates 'postgres' superuser
    password: process.env.POSTGRES_PASSWORD ? String(process.env.POSTGRES_PASSWORD) : '',
    max: 20,
    idleTimeoutMillis: 30000,
    connectionTimeoutMillis: 2000,
  });

  // Handle pool errors gracefully
  pool.on('error', (err) => {
    console.error('Unexpected PostgreSQL pool error:', err);
  });

  return pool;
}

export async function createTables(): Promise<void> {
  const client = await initPostgres().connect();
  try {
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
        score INTEGER DEFAULT 0,
        result_data JSONB,
        error_message TEXT,
        payload TEXT,
        response_data TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );

      CREATE INDEX IF NOT EXISTS idx_test_results_target ON test_results(target);
      CREATE INDEX IF NOT EXISTS idx_test_results_type ON test_results(test_type);
      CREATE INDEX IF NOT EXISTS idx_test_results_success ON test_results(success);
      CREATE INDEX IF NOT EXISTS idx_test_results_score ON test_results(score);
    `);

    await client.query(`
      CREATE TABLE IF NOT EXISTS training_data (
        id SERIAL PRIMARY KEY,
        source VARCHAR(50) NOT NULL,
        source_id VARCHAR(200),
        vulnerability_type VARCHAR(100) NOT NULL,
        target_pattern TEXT,
        payload_pattern TEXT,
        success_pattern TEXT,
        failure_pattern TEXT,
        context_data JSONB,
        score INTEGER DEFAULT 0,
        learned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );

      CREATE INDEX IF NOT EXISTS idx_training_source ON training_data(source);
      CREATE INDEX IF NOT EXISTS idx_training_type ON training_data(vulnerability_type);
    `);

    // Create graph tables
    await client.query(`
      CREATE TABLE IF NOT EXISTS graph_nodes (
        id VARCHAR(255) PRIMARY KEY,
        type VARCHAR(50) NOT NULL,
        label VARCHAR(500) NOT NULL,
        properties JSONB DEFAULT '{}',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );

      CREATE INDEX IF NOT EXISTS idx_nodes_type ON graph_nodes(type);
      CREATE INDEX IF NOT EXISTS idx_nodes_label ON graph_nodes(label);
      CREATE INDEX IF NOT EXISTS idx_nodes_properties ON graph_nodes USING GIN(properties);
    `);

    await client.query(`
      CREATE TABLE IF NOT EXISTS graph_edges (
        id SERIAL PRIMARY KEY,
        source VARCHAR(255) NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
        target VARCHAR(255) NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
        type VARCHAR(50) NOT NULL,
        weight DECIMAL(10, 2) DEFAULT 1.0,
        properties JSONB DEFAULT '{}',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(source, target, type)
      );

      CREATE INDEX IF NOT EXISTS idx_edges_source ON graph_edges(source);
      CREATE INDEX IF NOT EXISTS idx_edges_target ON graph_edges(target);
      CREATE INDEX IF NOT EXISTS idx_edges_type ON graph_edges(type);
      CREATE INDEX IF NOT EXISTS idx_edges_properties ON graph_edges USING GIN(properties);
    `);
  } finally {
    client.release();
  }
}

export async function saveFinding(finding: Finding): Promise<number> {
  const client = await initPostgres().connect();
  try {
    const result: QueryResult = await client.query(
      `INSERT INTO findings (target, type, severity, description, payload, response, score, timestamp)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
       RETURNING id`,
      [
        finding.target,
        finding.type,
        finding.severity,
        finding.description,
        finding.payload || null,
        finding.response || null,
        finding.score || 0,
        finding.timestamp,
      ]
    );
    return result.rows[0].id;
  } finally {
    client.release();
  }
}

export async function getFindings(
  target?: string,
  limit: number = 100
): Promise<Finding[]> {
  const client = await initPostgres().connect();
  try {
    let query = 'SELECT * FROM findings';
    const params: any[] = [];
    
    if (target) {
      query += ' WHERE target = $1';
      params.push(target);
    }
    
    query += ' ORDER BY timestamp DESC LIMIT $' + (params.length + 1);
    params.push(limit);

    const result: QueryResult = await client.query(query, params);
        return result.rows.map((row: any) => ({
      id: row.id.toString(),
      target: row.target,
      type: row.type,
      severity: row.severity,
      description: row.description,
      payload: row.payload,
      response: row.response,
      timestamp: row.timestamp,
      score: row.score,
    }));
  } finally {
    client.release();
  }
}

export async function saveTestResult(
  target: string,
  testType: string,
  success: boolean,
  resultData?: any,
  errorMessage?: string,
  score?: number,
  payload?: string,
  responseData?: string
): Promise<void> {
  const client = await initPostgres().connect();
  try {
    await client.query(
      `INSERT INTO test_results (target, test_type, success, result_data, error_message, score, payload, response_data)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8)`,
      [
        target,
        testType,
        success,
        JSON.stringify(resultData || {}),
        errorMessage || null,
        score || (success ? 5 : 0),
        payload || null,
        responseData || null
      ]
    );
  } finally {
    client.release();
  }
}

export async function getTestResults(
  target?: string,
  testType?: string,
  success?: boolean,
  limit: number = 100
): Promise<any[]> {
  const client = await initPostgres().connect();
  try {
    let query = 'SELECT * FROM test_results';
    const conditions: string[] = [];
    const params: any[] = [];
    let paramCount = 0;

    if (target) {
      paramCount++;
      conditions.push(`target = $${paramCount}`);
      params.push(target);
    }
    if (testType) {
      paramCount++;
      conditions.push(`test_type = $${paramCount}`);
      params.push(testType);
    }
    if (success !== undefined) {
      paramCount++;
      conditions.push(`success = $${paramCount}`);
      params.push(success);
    }

    if (conditions.length > 0) {
      query += ' WHERE ' + conditions.join(' AND ');
    }

    query += ' ORDER BY timestamp DESC LIMIT $' + (paramCount + 1);
    params.push(limit);

    const result: QueryResult = await client.query(query, params);
    return result.rows;
  } finally {
    client.release();
  }
}

export async function getTestStatistics(): Promise<any> {
  const client = await initPostgres().connect();
  try {
    const stats = await client.query(`
      SELECT 
        COUNT(*) as total_tests,
        COUNT(*) FILTER (WHERE success = true) as successful_tests,
        COUNT(*) FILTER (WHERE success = false) as failed_tests,
        AVG(score) as avg_score,
        test_type,
        COUNT(*) as count
      FROM test_results
      GROUP BY test_type
      ORDER BY count DESC
    `);
    return stats.rows;
  } finally {
    client.release();
  }
}

export async function saveTrainingData(
  source: string,
  sourceId: string,
  vulnerabilityType: string,
  targetPattern: string,
  payloadPattern: string,
  successPattern: string,
  failurePattern: string,
  contextData?: any,
  score?: number
): Promise<number> {
  const client = await initPostgres().connect();
  try {
    const result: QueryResult = await client.query(
      `INSERT INTO training_data (source, source_id, vulnerability_type, target_pattern, payload_pattern, success_pattern, failure_pattern, context_data, score)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
       RETURNING id`,
      [
        source,
        sourceId,
        vulnerabilityType,
        targetPattern,
        payloadPattern,
        successPattern,
        failurePattern,
        JSON.stringify(contextData || {}),
        score || 0
      ]
    );
    return result.rows[0].id;
  } finally {
    client.release();
  }
}

export async function getTrainingData(
  vulnerabilityType?: string,
  source?: string,
  limit: number = 100
): Promise<any[]> {
  const client = await initPostgres().connect();
  try {
    let query = 'SELECT * FROM training_data';
    const conditions: string[] = [];
    const params: any[] = [];
    let paramCount = 0;

    if (vulnerabilityType) {
      paramCount++;
      conditions.push(`vulnerability_type = $${paramCount}`);
      params.push(vulnerabilityType);
    }
    if (source) {
      paramCount++;
      conditions.push(`source = $${paramCount}`);
      params.push(source);
    }

    if (conditions.length > 0) {
      query += ' WHERE ' + conditions.join(' AND ');
    }

    query += ' ORDER BY learned_at DESC LIMIT $' + (paramCount + 1);
    params.push(limit);

    const result: QueryResult = await client.query(query, params);
    return result.rows;
  } finally {
    client.release();
  }
}

