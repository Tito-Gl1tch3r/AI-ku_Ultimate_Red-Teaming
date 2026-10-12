/**
 * Pattern detection algorithms for finding similar findings, patterns, and relationships
 */

import { GraphNode, GraphEdge, PatternMatch, Cluster, NodeType } from '../types/graph';
import { Finding } from '../types';
import { getFindings } from '../integrations/postgres';
import { getNodesByType, getNodeEdges } from '../integrations/graph';

/**
 * Calculate similarity between two strings (Jaccard similarity)
 */
export function calculateStringSimilarity(str1: string, str2: string): number {
  const set1 = new Set(str1.toLowerCase().split(/\s+/));
  const set2 = new Set(str2.toLowerCase().split(/\s+/));
  
  const intersection = new Set([...set1].filter(x => set2.has(x)));
  const union = new Set([...set1, ...set2]);
  
  return intersection.size / union.size;
}

/**
 * Extract patterns from findings
 */
export function extractPatternsFromFindings(findings: Finding[]): Map<string, any> {
  const patterns = new Map<string, any>();
  
  // Group by vulnerability type
  const byType = new Map<string, Finding[]>();
  findings.forEach(f => {
    if (!byType.has(f.type)) {
      byType.set(f.type, []);
    }
    byType.get(f.type)!.push(f);
  });
  
  // Extract common patterns
  byType.forEach((findings, type) => {
    const targets = new Set(findings.map(f => f.target));
    const commonPayloads = extractCommonPayloads(findings);
    const commonEndpoints = extractCommonEndpoints(findings);
    
    patterns.set(`type:${type}`, {
      type: 'vulnerability_type',
      vulnerability_type: type,
      count: findings.length,
      targets: Array.from(targets),
      common_payloads: commonPayloads,
      common_endpoints: commonEndpoints,
      severity_distribution: getSeverityDistribution(findings),
    });
  });
  
  return patterns;
}

/**
 * Extract common payloads from findings
 */
function extractCommonPayloads(findings: Finding[]): string[] {
  const payloadCounts = new Map<string, number>();
  
  findings.forEach(f => {
    if (f.payload) {
      const normalized = f.payload.trim().toLowerCase();
      payloadCounts.set(normalized, (payloadCounts.get(normalized) || 0) + 1);
    }
  });
  
  return Array.from(payloadCounts.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([payload]) => payload);
}

/**
 * Extract common endpoints from findings
 */
function extractCommonEndpoints(findings: Finding[]): string[] {
  const endpointCounts = new Map<string, number>();
  
  findings.forEach(f => {
    try {
      const url = new URL(f.target);
      const endpoint = url.pathname;
      endpointCounts.set(endpoint, (endpointCounts.get(endpoint) || 0) + 1);
    } catch (e) {
      // Invalid URL, skip
    }
  });
  
  return Array.from(endpointCounts.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([endpoint]) => endpoint);
}

/**
 * Get severity distribution
 */
function getSeverityDistribution(findings: Finding[]): Record<string, number> {
  const distribution: Record<string, number> = {
    low: 0,
    medium: 0,
    high: 0,
    critical: 0,
  };
  
  findings.forEach(f => {
    distribution[f.severity] = (distribution[f.severity] || 0) + 1;
  });
  
  return distribution;
}

/**
 * Find similar findings based on multiple criteria
 */
export async function findSimilarFindings(
  finding: Finding,
  threshold: number = 0.6
): Promise<Array<{ finding: Finding; similarity: number; reasons: string[] }>> {
  const allFindings = await getFindings();
  const similar: Array<{ finding: Finding; similarity: number; reasons: string[] }> = [];
  
  for (const other of allFindings) {
    if (other.id === finding.id) continue;
    
    const reasons: string[] = [];
    let similarity = 0;
    
    // Check type similarity
    if (other.type === finding.type) {
      similarity += 0.3;
      reasons.push('same_vulnerability_type');
    }
    
    // Check target similarity
    const targetSim = calculateStringSimilarity(other.target, finding.target);
    if (targetSim > 0.5) {
      similarity += targetSim * 0.2;
      reasons.push('similar_target');
    }
    
    // Check payload similarity
    if (finding.payload && other.payload) {
      const payloadSim = calculateStringSimilarity(finding.payload, other.payload);
      if (payloadSim > 0.5) {
        similarity += payloadSim * 0.3;
        reasons.push('similar_payload');
      }
    }
    
    // Check severity similarity
    if (other.severity === finding.severity) {
      similarity += 0.2;
      reasons.push('same_severity');
    }
    
    if (similarity >= threshold && reasons.length > 0) {
      similar.push({ finding: other, similarity, reasons });
    }
  }
  
  return similar.sort((a, b) => b.similarity - a.similarity);
}

/**
 * Cluster findings by similarity
 */
export async function clusterFindings(
  findings: Finding[],
  minClusterSize: number = 2
): Promise<Cluster[]> {
  const clusters: Cluster[] = [];
  const processed = new Set<string>();
  
  for (const finding of findings) {
    if (processed.has(finding.id || '')) continue;
    
    const similar = await findSimilarFindings(finding, 0.5);
    if (similar.length >= minClusterSize - 1) {
      const clusterNodes = [finding.id || '', ...similar.map(s => s.finding.id || '')].filter(Boolean);
      
      // Extract common properties
      const commonProperties: Record<string, any> = {
        type: finding.type,
        severity: finding.severity,
      };
      
      if (similar.length > 0) {
        const avgSimilarity = similar.reduce((sum, s) => sum + s.similarity, 0) / similar.length;
        commonProperties.avg_similarity = avgSimilarity;
      }
      
      clusters.push({
        id: `cluster:${finding.id}`,
        type: 'finding_cluster',
        nodes: clusterNodes,
        similarity_score: similar.length > 0 
          ? similar.reduce((sum, s) => sum + s.similarity, 0) / similar.length 
          : 0,
        common_properties: commonProperties,
      });
      
      clusterNodes.forEach(id => processed.add(id));
    }
  }
  
  return clusters;
}

/**
 * Detect patterns in graph structure
 */
export async function detectGraphPatterns(
  nodeType: NodeType,
  minOccurrences: number = 3
): Promise<PatternMatch[]> {
  const nodes = await getNodesByType(nodeType, 1000);
  const patterns: PatternMatch[] = [];
  
  // Group nodes by common properties
  const propertyGroups = new Map<string, GraphNode[]>();
  
  nodes.forEach(node => {
    Object.entries(node.properties || {}).forEach(([key, value]) => {
      if (typeof value === 'string' || typeof value === 'number') {
        const groupKey = `${key}:${value}`;
        if (!propertyGroups.has(groupKey)) {
          propertyGroups.set(groupKey, []);
        }
        propertyGroups.get(groupKey)!.push(node);
      }
    });
  });
  
  // Find patterns with enough occurrences
  propertyGroups.forEach((groupNodes, groupKey) => {
    if (groupNodes.length >= minOccurrences) {
      const [key, value] = groupKey.split(':');
      patterns.push({
        pattern_id: `pattern:${groupKey}`,
        pattern_type: `common_${key}`,
        matches: groupNodes.map(node => ({
          node_id: node.id,
          node_type: node.type,
          confidence: 1.0,
          details: { [key]: value },
        })),
        confidence: Math.min(1.0, groupNodes.length / 10), // Cap at 1.0
      });
    }
  });
  
  return patterns;
}

/**
 * Find attack chains (sequences of related findings)
 */
export async function findAttackChains(
  startNodeId: string,
  maxDepth: number = 3
): Promise<Array<{ path: string[]; nodes: GraphNode[]; weight: number }>> {
  const chains: Array<{ path: string[]; nodes: GraphNode[]; weight: number }> = [];
  const visited = new Set<string>();
  
  async function traverse(
    currentNodeId: string,
    currentPath: string[],
    currentWeight: number,
    depth: number
  ) {
    if (depth > maxDepth || visited.has(currentNodeId)) return;
    visited.add(currentNodeId);
    
    const edges = await getNodeEdges(currentNodeId, 'outgoing');
    
    for (const edge of edges) {
      const newPath = [...currentPath, edge.target];
      const newWeight = currentWeight + (edge.weight || 1.0);
      
      // Only follow certain edge types for attack chains
      if (['leads_to', 'related_to', 'uses', 'found_on'].includes(edge.type)) {
        if (depth >= 2) {
          // Found a chain of length >= 2
          chains.push({
            path: newPath,
            nodes: [], // Will be populated if needed
            weight: newWeight,
          });
        }
        
        await traverse(edge.target, newPath, newWeight, depth + 1);
      }
    }
    
    visited.delete(currentNodeId);
  }
  
  await traverse(startNodeId, [startNodeId], 0, 0);
  
  return chains.sort((a, b) => b.weight - a.weight);
}







