/**
 * Graph data structures for linking findings, patterns, and relationships
 */

export interface GraphNode {
  id: string;
  type: NodeType;
  label: string;
  properties: Record<string, any>;
  created_at?: Date;
}

export type NodeType =
  | 'target'
  | 'finding'
  | 'endpoint'
  | 'parameter'
  | 'subdomain'
  | 'vulnerability_type'
  | 'pattern'
  | 'payload'
  | 'test_result'
  | 'training_data';

export interface GraphEdge {
  id: string;
  source: string; // Node ID
  target: string; // Node ID
  type: EdgeType;
  weight?: number;
  properties: Record<string, any>;
  created_at?: Date;
}

export type EdgeType =
  | 'has_finding'
  | 'related_to'
  | 'similar_to'
  | 'contains'
  | 'uses'
  | 'leads_to'
  | 'matches_pattern'
  | 'found_on'
  | 'tested_with'
  | 'learned_from';

export interface Graph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface PatternMatch {
  pattern_id: string;
  pattern_type: string;
  matches: Array<{
    node_id: string;
    node_type: NodeType;
    confidence: number;
    details: Record<string, any>;
  }>;
  confidence: number;
}

export interface Cluster {
  id: string;
  type: string;
  nodes: string[]; // Node IDs
  similarity_score: number;
  common_properties: Record<string, any>;
}

export interface RelationshipPath {
  path: string[]; // Array of node IDs
  edges: string[]; // Array of edge IDs
  distance: number;
  weight: number;
}







