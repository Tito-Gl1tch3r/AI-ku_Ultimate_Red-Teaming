#!/usr/bin/env node

/**
 * Demonstration of Graph Tools Usage
 * 
 * This shows how to use the graph tools through MCP.
 * In Cursor/Claude Desktop, you would call these directly.
 */

console.log('🔍 Graph Tools Demonstration\n');
console.log('='.repeat(70));
console.log('\n📋 Available Graph Tools:\n');

const graphTools = [
  {
    name: 'graph.init',
    description: 'Initialize graph database tables',
    example: `await mcp.callTool('graph.init', {});`,
    result: 'Graph tables created successfully'
  },
  {
    name: 'graph.statistics',
    description: 'Get graph statistics',
    example: `await mcp.callTool('graph.statistics', {});`,
    result: {
      total_nodes: 150,
      total_edges: 300,
      finding_nodes: 50,
      target_nodes: 20
    }
  },
  {
    name: 'graph.extract_patterns',
    description: 'Extract patterns from findings',
    example: `await mcp.callTool('graph.extract_patterns', {});`,
    result: 'Returns patterns with common vulnerabilities, payloads, endpoints'
  },
  {
    name: 'graph.cluster_findings',
    description: 'Cluster similar findings',
    example: `await mcp.callTool('graph.cluster_findings', { minClusterSize: 2 });`,
    result: 'Groups of similar findings with similarity scores'
  },
  {
    name: 'graph.find_similar_findings',
    description: 'Find similar findings',
    example: `await mcp.callTool('graph.find_similar_findings', { findingId: 123, threshold: 0.6 });`,
    result: 'List of similar findings with similarity scores'
  },
  {
    name: 'graph.detect_patterns',
    description: 'Detect patterns in graph structure',
    example: `await mcp.callTool('graph.detect_patterns', { nodeType: 'finding', minOccurrences: 3 });`,
    result: 'Structural patterns in the graph'
  },
  {
    name: 'graph.find_related',
    description: 'Find related nodes',
    example: `await mcp.callTool('graph.find_related', { nodeId: 'finding:123', maxDepth: 2 });`,
    result: 'All nodes connected to the specified node'
  },
  {
    name: 'graph.find_attack_chains',
    description: 'Find attack chains',
    example: `await mcp.callTool('graph.find_attack_chains', { startNodeId: 'finding:123', maxDepth: 3 });`,
    result: 'Sequences of related findings (attack paths)'
  }
];

graphTools.forEach((tool, index) => {
  console.log(`${index + 1}. ${tool.name}`);
  console.log(`   ${tool.description}`);
  console.log(`   Example:`);
  console.log(`   ${tool.example}`);
  console.log(`   Result: ${typeof tool.result === 'object' ? JSON.stringify(tool.result, null, 2) : tool.result}`);
  console.log('');
});

console.log('='.repeat(70));
console.log('\n💡 How to Use in Cursor/Claude Desktop:\n');
console.log('1. Make sure the MCP server is running');
console.log('2. The tools are automatically available');
console.log('3. Call them using: await mcp.callTool(\'graph.<toolname>\', { ... });');
console.log('\n📝 Example Workflow:\n');

const workflow = `
// Step 1: Initialize graph
const initResult = await mcp.callTool('graph.init', {});
console.log(initResult.data.message);

// Step 2: Get statistics
const stats = await mcp.callTool('graph.statistics', {});
console.log('Total nodes:', stats.data.statistics.total_nodes);
console.log('Total findings:', stats.data.statistics.finding_nodes);

// Step 3: Extract patterns
const patterns = await mcp.callTool('graph.extract_patterns', {});
console.log('Patterns found:', patterns.data.count);
patterns.data.patterns.forEach(([key, pattern]) => {
  console.log(\`Pattern: \${key}, Count: \${pattern.count}\`);
});
`;

console.log(workflow);
console.log('\n✅ All graph tools are ready to use!\n');
console.log('📚 Documentation:');
console.log('   - QUICK_GRAPH_INSIGHTS.md (quick reference)');
console.log('   - GRAPH_INSIGHTS_GUIDE.md (detailed guide)');
console.log('   - GRAPH_ANALYSIS_GUIDE.md (complete guide)\n');







