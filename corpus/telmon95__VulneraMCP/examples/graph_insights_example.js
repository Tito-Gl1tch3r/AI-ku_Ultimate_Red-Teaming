#!/usr/bin/env node

/**
 * Example: Getting Insights from the Graph
 * 
 * This script demonstrates how to use the graph analysis tools
 * to extract valuable insights from your bug bounty data.
 */

// This is a conceptual example - in practice, you'd use the MCP tools
// through your MCP client (Cursor, Claude Desktop, etc.)

async function demonstrateGraphInsights() {
  console.log('🔍 Graph Insights Demonstration\n');
  console.log('='.repeat(60));
  
  // Step 1: Initialize Graph
  console.log('\n1️⃣  Initializing Graph...');
  console.log('   Command: graph.init');
  console.log('   Result: Graph tables created/verified');
  
  // Step 2: Get Statistics
  console.log('\n2️⃣  Getting Graph Statistics...');
  console.log('   Command: graph.statistics');
  console.log('   Example Result:');
  console.log('   {');
  console.log('     total_nodes: 150,');
  console.log('     total_edges: 300,');
  console.log('     finding_nodes: 50,');
  console.log('     target_nodes: 20');
  console.log('   }');
  
  // Step 3: Extract Patterns
  console.log('\n3️⃣  Extracting Patterns from Findings...');
  console.log('   Command: graph.extract_patterns');
  console.log('   This will:');
  console.log('   - Group findings by vulnerability type');
  console.log('   - Extract common payloads');
  console.log('   - Extract common endpoints');
  console.log('   - Calculate severity distributions');
  
  // Step 4: Find Similar Findings
  console.log('\n4️⃣  Finding Similar Findings...');
  console.log('   Command: graph.find_similar_findings');
  console.log('   Parameters: { findingId: 123, threshold: 0.6 }');
  console.log('   Returns: Findings with similar characteristics');
  
  // Step 5: Cluster Findings
  console.log('\n5️⃣  Clustering Findings...');
  console.log('   Command: graph.cluster_findings');
  console.log('   This groups similar findings together');
  console.log('   to identify common patterns');
  
  // Step 6: Detect Graph Patterns
  console.log('\n6️⃣  Detecting Graph Patterns...');
  console.log('   Command: graph.detect_patterns');
  console.log('   Parameters: { nodeType: "finding", minOccurrences: 3 }');
  console.log('   Finds structural patterns in the graph');
  
  // Step 7: Find Related Nodes
  console.log('\n7️⃣  Finding Related Nodes...');
  console.log('   Command: graph.find_related');
  console.log('   Parameters: { nodeId: "finding:123", maxDepth: 2 }');
  console.log('   Discovers all connected nodes');
  
  // Step 8: Find Attack Chains
  console.log('\n8️⃣  Finding Attack Chains...');
  console.log('   Command: graph.find_attack_chains');
  console.log('   Parameters: { startNodeId: "finding:123", maxDepth: 3 }');
  console.log('   Identifies sequences of related findings');
  
  console.log('\n' + '='.repeat(60));
  console.log('\n✅ Graph Insights Demonstration Complete!');
  console.log('\n📚 For detailed usage, see:');
  console.log('   - GRAPH_INSIGHTS_GUIDE.md');
  console.log('   - GRAPH_ANALYSIS_GUIDE.md');
}

// Run if executed directly
if (require.main === module) {
  demonstrateGraphInsights().catch(console.error);
}

module.exports = { demonstrateGraphInsights };







