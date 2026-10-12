/**
 * Graph database operations for linking findings and detecting patterns
 */

import { Pool, PoolClient, QueryResult } from 'pg';
import { GraphNode, GraphEdge, NodeType, EdgeType, PatternMatch, Cluster, RelationshipPath } from '../types/graph';
import { initPostgres } from './postgres';

/**
 * Create graph tables (nodes and edges)
 */
export async function createGraphTables(): Promise<void> {
  const pool = initPostgres();
  const client = await pool.connect();
  try {
    // Nodes table
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

    // Edges table
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

/**
 * Create or update a graph node
 */
export async function upsertNode(node: GraphNode): Promise<void> {
  const pool = initPostgres();
  const client = await pool.connect();
  try {
    await client.query(
      `INSERT INTO graph_nodes (id, type, label, properties, created_at)
       VALUES ($1, $2, $3, $4, $5)
       ON CONFLICT (id) 
       DO UPDATE SET 
         type = EXCLUDED.type,
         label = EXCLUDED.label,
         properties = EXCLUDED.properties`,
      [
        node.id,
        node.type,
        node.label,
        JSON.stringify(node.properties || {}),
        node.created_at || new Date(),
      ]
    );
  } finally {
    client.release();
  }
}

/**
 * Create or update a graph edge
 */
export async function upsertEdge(edge: GraphEdge): Promise<void> {
  const pool = initPostgres();
  const client = await pool.connect();
  try {
    await client.query(
      `INSERT INTO graph_edges (source, target, type, weight, properties, created_at)
       VALUES ($1, $2, $3, $4, $5, $6)
       ON CONFLICT (source, target, type)
       DO UPDATE SET 
         weight = EXCLUDED.weight,
         properties = EXCLUDED.properties`,
      [
        edge.source,
        edge.target,
        edge.type,
        edge.weight || 1.0,
        JSON.stringify(edge.properties || {}),
        edge.created_at || new Date(),
      ]
    );
  } finally {
    client.release();
  }
}

/**
 * Get node by ID
 */
export async function getNode(nodeId: string): Promise<GraphNode | null> {
  const pool = initPostgres();
  const client = await pool.connect();
  try {
    const result = await client.query(
      'SELECT * FROM graph_nodes WHERE id = $1',
      [nodeId]
    );
    if (result.rows.length === 0) return null;
    const row = result.rows[0];
    return {
      id: row.id,
      type: row.type as NodeType,
      label: row.label,
      properties: row.properties || {},
      created_at: row.created_at,
    };
  } finally {
    client.release();
  }
}

/**
 * Get nodes by type
 */
export async function getNodesByType(type: NodeType, limit: number = 100): Promise<GraphNode[]> {
  const pool = initPostgres();
  const client = await pool.connect();
  try {
    const result = await client.query(
      'SELECT * FROM graph_nodes WHERE type = $1 ORDER BY created_at DESC LIMIT $2',
      [type, limit]
    );
    return result.rows.map((row: any) => ({
      id: row.id,
      type: row.type as NodeType,
      label: row.label,
      properties: row.properties || {},
      created_at: row.created_at,
    }));
  } finally {
    client.release();
  }
}

/**
 * Get edges for a node
 */
export async function getNodeEdges(
  nodeId: string,
  direction: 'incoming' | 'outgoing' | 'both' = 'both'
): Promise<GraphEdge[]> {
  const pool = initPostgres();
  const client = await pool.connect();
  try {
    let query = '';
    if (direction === 'incoming') {
      query = 'SELECT * FROM graph_edges WHERE target = $1';
    } else if (direction === 'outgoing') {
      query = 'SELECT * FROM graph_edges WHERE source = $1';
    } else {
      query = 'SELECT * FROM graph_edges WHERE source = $1 OR target = $1';
    }
    const result = await client.query(query + ' ORDER BY created_at DESC', [nodeId]);
    return result.rows.map((row: any) => ({
      id: row.id.toString(),
      source: row.source,
      target: row.target,
      type: row.type as EdgeType,
      weight: parseFloat(row.weight),
      properties: row.properties || {},
      created_at: row.created_at,
    }));
  } finally {
    client.release();
  }
}

/**
 * Find related nodes (nodes connected to a given node)
 */
export async function findRelatedNodes(
  nodeId: string,
  maxDepth: number = 2,
  limit: number = 50
): Promise<GraphNode[]> {
  const pool = initPostgres();
  const client = await pool.connect();
  try {
    // Use recursive CTE to find nodes within maxDepth
    const result = await client.query(
      `WITH RECURSIVE related AS (
        SELECT target as node_id, 1 as depth
        FROM graph_edges WHERE source = $1
        UNION
        SELECT e.target, r.depth + 1
        FROM graph_edges e
        INNER JOIN related r ON e.source = r.node_id
        WHERE r.depth < $2
      )
      SELECT DISTINCT n.*
      FROM related r
      JOIN graph_nodes n ON n.id = r.node_id
      LIMIT $3`,
      [nodeId, maxDepth, limit]
    );
    return result.rows.map((row: any) => ({
      id: row.id,
      type: row.type as NodeType,
      label: row.label,
      properties: row.properties || {},
      created_at: row.created_at,
    }));
  } finally {
    client.release();
  }
}

/**
 * Find path between two nodes
 */
export async function findPath(
  sourceId: string,
  targetId: string,
  maxDepth: number = 5
): Promise<RelationshipPath | null> {
  const pool = initPostgres();
  const client = await pool.connect();
  try {
    const result = await client.query(
      `WITH RECURSIVE path AS (
        SELECT 
          source,
          target,
          ARRAY[source, target] as path,
          ARRAY[id::text] as edges,
          1 as depth,
          weight
        FROM graph_edges
        WHERE source = $1
        UNION ALL
        SELECT 
          e.source,
          e.target,
          p.path || e.target,
          p.edges || e.id::text,
          p.depth + 1,
          p.weight + e.weight
        FROM graph_edges e
        INNER JOIN path p ON e.source = p.target
        WHERE p.depth < $2
          AND NOT e.target = ANY(p.path)
      )
      SELECT path, edges, depth as distance, weight
      FROM path
      WHERE target = $3
      ORDER BY depth, weight
      LIMIT 1`,
      [sourceId, maxDepth, targetId]
    );

    if (result.rows.length === 0) return null;

    const row = result.rows[0];
    return {
      path: row.path,
      edges: row.edges,
      distance: row.distance,
      weight: parseFloat(row.weight),
    };
  } finally {
    client.release();
  }
}

/**
 * Link finding to target
 */
export async function linkFindingToTarget(findingId: number, target: string): Promise<void> {
  const targetNodeId = `target:${target}`;
  const findingNodeId = `finding:${findingId}`;

  // Create target node
  await upsertNode({
    id: targetNodeId,
    type: 'target',
    label: target,
    properties: { url: target },
  });

  // Create finding node
  await upsertNode({
    id: findingNodeId,
    type: 'finding',
    label: `Finding #${findingId}`,
    properties: { finding_id: findingId },
  });

  // Create edge
  await upsertEdge({
    id: `edge:${findingNodeId}:${targetNodeId}`,
    source: targetNodeId,
    target: findingNodeId,
    type: 'has_finding',
    weight: 1.0,
    properties: {},
  });
}

/**
 * Link related findings
 */
export async function linkRelatedFindings(
  findingId1: number,
  findingId2: number,
  similarity: number,
  reason: string
): Promise<void> {
  const nodeId1 = `finding:${findingId1}`;
  const nodeId2 = `finding:${findingId2}`;

  await upsertEdge({
    id: `edge:${nodeId1}:${nodeId2}`,
    source: nodeId1,
    target: nodeId2,
    type: 'related_to',
    weight: similarity,
    properties: { reason, similarity },
  });
}

/**
 * Get graph statistics
 */
export async function getGraphStatistics(): Promise<any> {
  const pool = initPostgres();
  const client = await pool.connect();
  try {
    const stats = await client.query(`
      SELECT 
        (SELECT COUNT(*) FROM graph_nodes) as total_nodes,
        (SELECT COUNT(*) FROM graph_edges) as total_edges,
        (SELECT COUNT(DISTINCT type) FROM graph_nodes) as node_types,
        (SELECT COUNT(DISTINCT type) FROM graph_edges) as edge_types,
        (SELECT COUNT(*) FROM graph_nodes WHERE type = 'finding') as finding_nodes,
        (SELECT COUNT(*) FROM graph_nodes WHERE type = 'target') as target_nodes
    `);
    return stats.rows[0];
  } finally {
    client.release();
  }
}







