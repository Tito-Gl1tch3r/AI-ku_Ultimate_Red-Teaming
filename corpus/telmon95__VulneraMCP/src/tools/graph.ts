/**
 * Graph analysis and pattern detection tools
 */

import { Server } from '../mcp/server';
import { formatToolResult, ToolResult } from '../types';
import {
  createGraphTables,
  upsertNode,
  upsertEdge,
  getNode,
  getNodesByType,
  getNodeEdges,
  findRelatedNodes,
  findPath,
  linkFindingToTarget,
  linkRelatedFindings,
  getGraphStatistics,
} from '../integrations/graph';
import {
  extractPatternsFromFindings,
  findSimilarFindings,
  clusterFindings,
  detectGraphPatterns,
  findAttackChains,
} from '../utils/pattern_detection';
import { getFindings } from '../integrations/postgres';
import { GraphNode, GraphEdge, NodeType, EdgeType } from '../types/graph';

export function registerGraphTools(server: Server) {
  // Initialize graph tables
  server.tool(
    'graph.init',
    {
      description: 'Initialize graph database tables (nodes and edges)',
      inputSchema: {
        type: 'object',
        properties: {},
        required: [],
      },
    },
    async (): Promise<ToolResult> => {
      try {
        await createGraphTables();
        return formatToolResult(true, { message: 'Graph tables initialized successfully' });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Create or update a node
  server.tool(
    'graph.create_node',
    {
      description: 'Create or update a graph node',
      inputSchema: {
        type: 'object',
        properties: {
          id: { type: 'string', description: 'Unique node ID' },
          type: {
            type: 'string',
            enum: ['target', 'finding', 'endpoint', 'parameter', 'subdomain', 'vulnerability_type', 'pattern', 'payload', 'test_result', 'training_data'],
            description: 'Node type',
          },
          label: { type: 'string', description: 'Node label' },
          properties: { type: 'object', description: 'Node properties as key-value pairs' },
        },
        required: ['id', 'type', 'label'],
      },
    },
    async ({ id, type, label, properties = {} }: any): Promise<ToolResult> => {
      try {
        const node: GraphNode = {
          id,
          type: type as NodeType,
          label,
          properties,
        };
        await upsertNode(node);
        return formatToolResult(true, { node });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Create or update an edge
  server.tool(
    'graph.create_edge',
    {
      description: 'Create or update a graph edge (relationship)',
      inputSchema: {
        type: 'object',
        properties: {
          source: { type: 'string', description: 'Source node ID' },
          target: { type: 'string', description: 'Target node ID' },
          type: {
            type: 'string',
            enum: ['has_finding', 'related_to', 'similar_to', 'contains', 'uses', 'leads_to', 'matches_pattern', 'found_on', 'tested_with', 'learned_from'],
            description: 'Edge type',
          },
          weight: { type: 'number', description: 'Edge weight (default: 1.0)' },
          properties: { type: 'object', description: 'Edge properties' },
        },
        required: ['source', 'target', 'type'],
      },
    },
    async ({ source, target, type, weight, properties = {} }: any): Promise<ToolResult> => {
      try {
        const edge: GraphEdge = {
          id: `edge:${source}:${target}:${type}`,
          source,
          target,
          type: type as EdgeType,
          weight,
          properties,
        };
        await upsertEdge(edge);
        return formatToolResult(true, { edge });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Get node
  server.tool(
    'graph.get_node',
    {
      description: 'Get a graph node by ID',
      inputSchema: {
        type: 'object',
        properties: {
          nodeId: { type: 'string', description: 'Node ID' },
        },
        required: ['nodeId'],
      },
    },
    async ({ nodeId }: any): Promise<ToolResult> => {
      try {
        const node = await getNode(nodeId);
        if (!node) {
          return formatToolResult(false, null, 'Node not found');
        }
        return formatToolResult(true, { node });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Get nodes by type
  server.tool(
    'graph.get_nodes_by_type',
    {
      description: 'Get all nodes of a specific type',
      inputSchema: {
        type: 'object',
        properties: {
          type: {
            type: 'string',
            enum: ['target', 'finding', 'endpoint', 'parameter', 'subdomain', 'vulnerability_type', 'pattern', 'payload', 'test_result', 'training_data'],
            description: 'Node type',
          },
          limit: { type: 'number', description: 'Maximum number of nodes to return', default: 100 },
        },
        required: ['type'],
      },
    },
    async ({ type, limit = 100 }: any): Promise<ToolResult> => {
      try {
        const nodes = await getNodesByType(type as NodeType, limit);
        return formatToolResult(true, { nodes, count: nodes.length });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Get node edges
  server.tool(
    'graph.get_node_edges',
    {
      description: 'Get edges connected to a node',
      inputSchema: {
        type: 'object',
        properties: {
          nodeId: { type: 'string', description: 'Node ID' },
          direction: {
            type: 'string',
            enum: ['incoming', 'outgoing', 'both'],
            description: 'Edge direction',
            default: 'both',
          },
        },
        required: ['nodeId'],
      },
    },
    async ({ nodeId, direction = 'both' }: any): Promise<ToolResult> => {
      try {
        const edges = await getNodeEdges(nodeId, direction as 'incoming' | 'outgoing' | 'both');
        return formatToolResult(true, { edges, count: edges.length });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Find related nodes
  server.tool(
    'graph.find_related',
    {
      description: 'Find nodes related to a given node (within max depth)',
      inputSchema: {
        type: 'object',
        properties: {
          nodeId: { type: 'string', description: 'Starting node ID' },
          maxDepth: { type: 'number', description: 'Maximum depth to search', default: 2 },
          limit: { type: 'number', description: 'Maximum number of nodes to return', default: 50 },
        },
        required: ['nodeId'],
      },
    },
    async ({ nodeId, maxDepth = 2, limit = 50 }: any): Promise<ToolResult> => {
      try {
        const nodes = await findRelatedNodes(nodeId, maxDepth, limit);
        return formatToolResult(true, { nodes, count: nodes.length });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Find path between nodes
  server.tool(
    'graph.find_path',
    {
      description: 'Find shortest path between two nodes',
      inputSchema: {
        type: 'object',
        properties: {
          sourceId: { type: 'string', description: 'Source node ID' },
          targetId: { type: 'string', description: 'Target node ID' },
          maxDepth: { type: 'number', description: 'Maximum path depth', default: 5 },
        },
        required: ['sourceId', 'targetId'],
      },
    },
    async ({ sourceId, targetId, maxDepth = 5 }: any): Promise<ToolResult> => {
      try {
        const path = await findPath(sourceId, targetId, maxDepth);
        if (!path) {
          return formatToolResult(false, null, 'No path found between nodes');
        }
        return formatToolResult(true, { path });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Link finding to target
  server.tool(
    'graph.link_finding_to_target',
    {
      description: 'Link a finding to its target in the graph',
      inputSchema: {
        type: 'object',
        properties: {
          findingId: { type: 'number', description: 'Finding ID from database' },
          target: { type: 'string', description: 'Target URL or domain' },
        },
        required: ['findingId', 'target'],
      },
    },
    async ({ findingId, target }: any): Promise<ToolResult> => {
      try {
        await linkFindingToTarget(findingId, target);
        return formatToolResult(true, {
          message: `Finding #${findingId} linked to target ${target}`,
        });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Link related findings
  server.tool(
    'graph.link_related_findings',
    {
      description: 'Link two findings as related',
      inputSchema: {
        type: 'object',
        properties: {
          findingId1: { type: 'number', description: 'First finding ID' },
          findingId2: { type: 'number', description: 'Second finding ID' },
          similarity: { type: 'number', description: 'Similarity score (0-1)', default: 0.5 },
          reason: { type: 'string', description: 'Reason for linking' },
        },
        required: ['findingId1', 'findingId2'],
      },
    },
    async ({ findingId1, findingId2, similarity = 0.5, reason = 'related' }: any): Promise<ToolResult> => {
      try {
        await linkRelatedFindings(findingId1, findingId2, similarity, reason);
        return formatToolResult(true, {
          message: `Findings #${findingId1} and #${findingId2} linked`,
        });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Extract patterns from findings
  server.tool(
    'graph.extract_patterns',
    {
      description: 'Extract patterns from findings and create pattern nodes',
      inputSchema: {
        type: 'object',
        properties: {
          target: { type: 'string', description: 'Filter by target (optional)' },
        },
        required: [],
      },
    },
    async ({ target }: any): Promise<ToolResult> => {
      try {
        const findings = await getFindings(target);
        const patterns = extractPatternsFromFindings(findings);
        
        // Create pattern nodes
        const patternNodes: GraphNode[] = [];
        patterns.forEach((pattern, key) => {
          const node: GraphNode = {
            id: `pattern:${key}`,
            type: 'pattern',
            label: `Pattern: ${pattern.vulnerability_type || key}`,
            properties: pattern,
          };
          patternNodes.push(node);
          upsertNode(node);
        });
        
        return formatToolResult(true, {
          patterns: Array.from(patterns.entries()),
          patternNodes,
          count: patterns.size,
        });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Find similar findings
  server.tool(
    'graph.find_similar_findings',
    {
      description: 'Find findings similar to a given finding',
      inputSchema: {
        type: 'object',
        properties: {
          findingId: { type: 'number', description: 'Finding ID to compare against' },
          threshold: { type: 'number', description: 'Similarity threshold (0-1)', default: 0.6 },
        },
        required: ['findingId'],
      },
    },
    async ({ findingId, threshold = 0.6 }: any): Promise<ToolResult> => {
      try {
        const findings = await getFindings();
        const finding = findings.find(f => f.id === findingId.toString());
        
        if (!finding) {
          return formatToolResult(false, null, 'Finding not found');
        }
        
        const similar = await findSimilarFindings(finding, threshold);
        return formatToolResult(true, {
          finding,
          similar,
          count: similar.length,
        });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Cluster findings
  server.tool(
    'graph.cluster_findings',
    {
      description: 'Cluster findings by similarity',
      inputSchema: {
        type: 'object',
        properties: {
          target: { type: 'string', description: 'Filter by target (optional)' },
          minClusterSize: { type: 'number', description: 'Minimum cluster size', default: 2 },
        },
        required: [],
      },
    },
    async ({ target, minClusterSize = 2 }: any): Promise<ToolResult> => {
      try {
        const findings = await getFindings(target);
        const clusters = await clusterFindings(findings, minClusterSize);
        return formatToolResult(true, {
          clusters,
          count: clusters.length,
        });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Detect graph patterns
  server.tool(
    'graph.detect_patterns',
    {
      description: 'Detect patterns in the graph structure',
      inputSchema: {
        type: 'object',
        properties: {
          nodeType: {
            type: 'string',
            enum: ['target', 'finding', 'endpoint', 'parameter', 'subdomain', 'vulnerability_type', 'pattern', 'payload', 'test_result', 'training_data'],
            description: 'Node type to analyze',
          },
          minOccurrences: { type: 'number', description: 'Minimum occurrences for a pattern', default: 3 },
        },
        required: ['nodeType'],
      },
    },
    async ({ nodeType, minOccurrences = 3 }: any): Promise<ToolResult> => {
      try {
        const patterns = await detectGraphPatterns(nodeType as NodeType, minOccurrences);
        return formatToolResult(true, {
          patterns,
          count: patterns.length,
        });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Find attack chains
  server.tool(
    'graph.find_attack_chains',
    {
      description: 'Find attack chains (sequences of related findings)',
      inputSchema: {
        type: 'object',
        properties: {
          startNodeId: { type: 'string', description: 'Starting node ID' },
          maxDepth: { type: 'number', description: 'Maximum chain depth', default: 3 },
        },
        required: ['startNodeId'],
      },
    },
    async ({ startNodeId, maxDepth = 3 }: any): Promise<ToolResult> => {
      try {
        const chains = await findAttackChains(startNodeId, maxDepth);
        return formatToolResult(true, {
          chains,
          count: chains.length,
        });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Generate attack graph from findings
  server.tool(
    'attackgraph.generate',
    {
      description: 'Generate an attack graph from findings and persist nodes/edges',
      inputSchema: {
        type: 'object',
        properties: {
          target: { type: 'string', description: 'Target filter (optional)' },
          persist: { type: 'boolean', description: 'Persist nodes/edges in graph tables', default: true },
          limit: { type: 'number', description: 'Max findings to include', default: 200 },
        },
      },
    },
    async ({ target, persist = true, limit = 200 }: any): Promise<ToolResult> => {
      try {
        const graph = await buildAttackGraph(target, limit);
        if (persist) {
          for (const node of graph.nodes) {
            await upsertNode(node);
          }
          for (const edge of graph.edges) {
            await upsertEdge(edge);
          }
        }
        return formatToolResult(true, {
          nodes: graph.nodes,
          edges: graph.edges,
          counts: { nodes: graph.nodes.length, edges: graph.edges.length },
        });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  server.tool(
    'attackgraph.export_json',
    {
      description: 'Export an attack graph (JSON) from findings without DB dependency',
      inputSchema: {
        type: 'object',
        properties: {
          target: { type: 'string', description: 'Target filter (optional)' },
          limit: { type: 'number', description: 'Max findings to include', default: 200 },
        },
      },
    },
    async ({ target, limit = 200 }: any): Promise<ToolResult> => {
      try {
        const graph = await buildAttackGraph(target, limit);
        return formatToolResult(true, graph);
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  server.tool(
    'attackgraph.export_visual_json',
    {
      description: 'Export visualization-ready JSON with node/edge styling',
      inputSchema: {
        type: 'object',
        properties: {
          target: { type: 'string', description: 'Target filter (optional)' },
          limit: { type: 'number', description: 'Max findings to include', default: 200 },
        },
      },
    },
    async ({ target, limit = 200 }: any): Promise<ToolResult> => {
      try {
        const graph = await buildAttackGraph(target, limit);
        const visual = toVisualGraph(graph.nodes, graph.edges);
        return formatToolResult(true, visual);
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  server.tool(
    'attackgraph.export_graphml',
    {
      description: 'Export attack graph to GraphML format',
      inputSchema: {
        type: 'object',
        properties: {
          target: { type: 'string', description: 'Target filter (optional)' },
          limit: { type: 'number', description: 'Max findings to include', default: 200 },
        },
      },
    },
    async ({ target, limit = 200 }: any): Promise<ToolResult> => {
      try {
        const graph = await buildAttackGraph(target, limit);
        const graphml = toGraphML(graph.nodes, graph.edges);
        return formatToolResult(true, { graphml });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  server.tool(
    'attackgraph.rank_paths',
    {
      description: 'Rank attack paths by severity and evidence strength',
      inputSchema: {
        type: 'object',
        properties: {
          target: { type: 'string', description: 'Target filter (optional)' },
          limit: { type: 'number', description: 'Max findings to include', default: 200 },
        },
      },
    },
    async ({ target, limit = 200 }: any): Promise<ToolResult> => {
      try {
        const graph = await buildAttackGraph(target, limit);
        const paths = graph.nodes
          .filter((n) => n.type === 'finding')
          .map((finding) => {
            const vulnEdge = graph.edges.find(
              (e) => e.source === finding.id && e.type === 'leads_to'
            );
            const vulnNode = vulnEdge
              ? graph.nodes.find((n) => n.id === vulnEdge.target)
              : null;
            const endpointEdge = graph.edges.find(
              (e) => e.source === finding.id && e.type === 'found_on'
            );
            const endpointNode = endpointEdge
              ? graph.nodes.find((n) => n.id === endpointEdge.target)
              : null;
            const severityScore = severityToScore(finding.properties?.severity || 'low');
            return {
              finding: finding.label,
              severity: finding.properties?.severity || 'low',
              score: severityScore,
              endpoint: endpointNode?.label || null,
              vulnerability: vulnNode?.label || null,
            };
          })
          .sort((a, b) => b.score - a.score);
        return formatToolResult(true, { paths, count: paths.length });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Get graph statistics
  server.tool(
    'graph.statistics',
    {
      description: 'Get graph statistics (nodes, edges, types, etc.)',
      inputSchema: {
        type: 'object',
        properties: {},
        required: [],
      },
    },
    async (): Promise<ToolResult> => {
      try {
        const stats = await getGraphStatistics();
        return formatToolResult(true, { statistics: stats });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );
}

async function buildAttackGraph(target?: string, limit: number = 200): Promise<{ nodes: GraphNode[]; edges: GraphEdge[] }> {
  const findings = await getFindings(target, limit);
  const nodes: GraphNode[] = [];
  const edges: GraphEdge[] = [];

  const targetLabel = target || 'all';
  const targetNodeId = `target:${targetLabel}`;
  nodes.push({
    id: targetNodeId,
    type: 'target',
    label: targetLabel,
    properties: { target: target || 'all' },
  });

  for (const finding of findings) {
    const findingId = finding.id || `${finding.target}:${finding.type}:${finding.timestamp}`;
    const findingNodeId = `finding:${findingId}`;
    nodes.push({
      id: findingNodeId,
      type: 'finding',
      label: `${finding.type}`,
      properties: {
        finding_id: finding.id,
        severity: finding.severity,
        description: finding.description,
        target: finding.target,
        score: finding.score,
      },
    });
    edges.push({
      id: `edge:${targetNodeId}:${findingNodeId}:has_finding`,
      source: targetNodeId,
      target: findingNodeId,
      type: 'has_finding',
      weight: severityToScore(finding.severity),
      properties: {},
    });

    const vulnNodeId = `vuln:${finding.type}`;
    nodes.push({
      id: vulnNodeId,
      type: 'vulnerability_type',
      label: finding.type,
      properties: {},
    });
    edges.push({
      id: `edge:${findingNodeId}:${vulnNodeId}:leads_to`,
      source: findingNodeId,
      target: vulnNodeId,
      type: 'leads_to',
      weight: severityToScore(finding.severity),
      properties: {},
    });

    if (finding.target) {
      try {
        const url = new URL(finding.target.startsWith('http') ? finding.target : `https://${finding.target}`);
        const endpointNodeId = `endpoint:${url.host}${url.pathname}`;
        nodes.push({
          id: endpointNodeId,
          type: 'endpoint',
          label: `${url.host}${url.pathname}`,
          properties: { host: url.host, path: url.pathname },
        });
        edges.push({
          id: `edge:${findingNodeId}:${endpointNodeId}:found_on`,
          source: findingNodeId,
          target: endpointNodeId,
          type: 'found_on',
          weight: 1.0,
          properties: {},
        });
      } catch {
        // ignore non-URL targets
      }
    }
  }

  return { nodes, edges };
}

function severityToScore(severity: string | undefined): number {
  switch (severity) {
    case 'critical':
      return 4;
    case 'high':
      return 3;
    case 'medium':
      return 2;
    case 'low':
    default:
      return 1;
  }
}

function toVisualGraph(nodes: GraphNode[], edges: GraphEdge[]) {
  const styledNodes = nodes.map((node) => {
    const severity = node.properties?.severity as string | undefined;
    const color = severityToColor(severity);
    return {
      id: node.id,
      label: node.label,
      type: node.type,
      properties: node.properties,
      style: {
        color,
        size: node.type === 'finding' ? 20 : node.type === 'target' ? 24 : 16,
      },
    };
  });

  const styledEdges = edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    type: edge.type,
    weight: edge.weight || 1,
  }));

  return { nodes: styledNodes, edges: styledEdges };
}

function severityToColor(severity: string | undefined): string {
  switch (severity) {
    case 'critical':
      return '#d9534f';
    case 'high':
      return '#f0ad4e';
    case 'medium':
      return '#ffd500';
    case 'low':
    default:
      return '#5bc0de';
  }
}

function toGraphML(nodes: GraphNode[], edges: GraphEdge[]): string {
  const nodeXml = nodes
    .map(
      (node) =>
        `<node id="${escapeXml(node.id)}"><data key="label">${escapeXml(node.label)}</data><data key="type">${escapeXml(node.type)}</data></node>`
    )
    .join('');

  const edgeXml = edges
    .map(
      (edge) =>
        `<edge source="${escapeXml(edge.source)}" target="${escapeXml(edge.target)}"><data key="type">${escapeXml(edge.type)}</data><data key="weight">${edge.weight || 1}</data></edge>`
    )
    .join('');

  return `<?xml version="1.0" encoding="UTF-8"?>` +
    `<graphml xmlns="http://graphml.graphdrawing.org/xmlns">` +
    `<key id="label" for="node" attr.name="label" attr.type="string"/>` +
    `<key id="type" for="node" attr.name="type" attr.type="string"/>` +
    `<key id="type" for="edge" attr.name="type" attr.type="string"/>` +
    `<key id="weight" for="edge" attr.name="weight" attr.type="double"/>` +
    `<graph id="attackgraph" edgedefault="directed">` +
    nodeXml +
    edgeXml +
    `</graph></graphml>`;
}

function escapeXml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}







