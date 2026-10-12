#!/usr/bin/env node

/**
 * Complete Graph Workflow Example
 * 
 * Demonstrates all graph tools working together in a realistic workflow
 */

console.log('🔍 Complete Graph Workflow Demonstration\n');
console.log('='.repeat(70));

async function completeGraphWorkflow() {
  console.log('\n📋 Step-by-Step Graph Analysis Workflow\n');
  
  // Step 1: Initialize Graph
  console.log('1️⃣  INITIALIZING GRAPH');
  console.log('   Tool: graph.init');
  console.log('   Command: await mcp.callTool("graph.init", {});');
  console.log('   Purpose: Create graph database tables (nodes and edges)');
  console.log('   Result: ✅ Graph tables initialized successfully\n');
  
  // Step 2: Get Statistics
  console.log('2️⃣  GETTING GRAPH STATISTICS');
  console.log('   Tool: graph.statistics');
  console.log('   Command: await mcp.callTool("graph.statistics", {});');
  console.log('   Purpose: Get overview of your graph data');
  console.log('   Returns:');
  console.log('   {');
  console.log('     total_nodes: 150,');
  console.log('     total_edges: 300,');
  console.log('     finding_nodes: 50,');
  console.log('     target_nodes: 20,');
  console.log('     node_types: 8,');
  console.log('     edge_types: 6');
  console.log('   }\n');
  
  // Step 3: Extract Patterns
  console.log('3️⃣  EXTRACTING PATTERNS FROM FINDINGS');
  console.log('   Tool: graph.extract_patterns');
  console.log('   Command: await mcp.callTool("graph.extract_patterns", {});');
  console.log('   Purpose: Find common vulnerability patterns');
  console.log('   What it does:');
  console.log('   - Groups findings by vulnerability type');
  console.log('   - Extracts common payloads');
  console.log('   - Extracts common endpoints');
  console.log('   - Calculates severity distributions');
  console.log('   - Creates pattern nodes automatically');
  console.log('   Returns: Patterns with counts, endpoints, payloads, severity\n');
  
  // Step 4: Cluster Findings
  console.log('4️⃣  CLUSTERING FINDINGS');
  console.log('   Tool: graph.cluster_findings');
  console.log('   Command: await mcp.callTool("graph.cluster_findings", { minClusterSize: 2 });');
  console.log('   Purpose: Group similar findings together');
  console.log('   What it does:');
  console.log('   - Finds findings with similar characteristics');
  console.log('   - Groups them into clusters');
  console.log('   - Calculates similarity scores');
  console.log('   - Identifies common properties');
  console.log('   Returns: Clusters with similarity scores and common properties\n');
  
  // Step 5: Find Similar Findings
  console.log('5️⃣  FINDING SIMILAR FINDINGS');
  console.log('   Tool: graph.find_similar_findings');
  console.log('   Command: await mcp.callTool("graph.find_similar_findings", {');
  console.log('     findingId: 123,');
  console.log('     threshold: 0.6');
  console.log('   });');
  console.log('   Purpose: Find findings similar to a specific finding');
  console.log('   Similarity based on:');
  console.log('   - Same vulnerability type (30%)');
  console.log('   - Similar target (20%)');
  console.log('   - Similar payload (30%)');
  console.log('   - Same severity (20%)');
  console.log('   Returns: List of similar findings with similarity scores and reasons\n');
  
  // Step 6: Detect Patterns
  console.log('6️⃣  DETECTING GRAPH PATTERNS');
  console.log('   Tool: graph.detect_patterns');
  console.log('   Command: await mcp.callTool("graph.detect_patterns", {');
  console.log('     nodeType: "finding",');
  console.log('     minOccurrences: 3');
  console.log('   });');
  console.log('   Purpose: Find structural patterns in the graph');
  console.log('   What it does:');
  console.log('   - Analyzes graph structure');
  console.log('   - Finds common node properties');
  console.log('   - Detects recurring patterns');
  console.log('   - Calculates confidence scores');
  console.log('   Returns: Patterns with matches and confidence levels\n');
  
  // Step 7: Find Related Nodes
  console.log('7️⃣  FINDING RELATED NODES');
  console.log('   Tool: graph.find_related');
  console.log('   Command: await mcp.callTool("graph.find_related", {');
  console.log('     nodeId: "finding:123",');
  console.log('     maxDepth: 2');
  console.log('   });');
  console.log('   Purpose: Discover all nodes connected to a specific node');
  console.log('   What it does:');
  console.log('   - Traverses the graph from a starting node');
  console.log('   - Finds all connected nodes within max depth');
  console.log('   - Shows the relationship network');
  console.log('   Returns: List of related nodes with their properties\n');
  
  // Step 8: Find Attack Chains
  console.log('8️⃣  FINDING ATTACK CHAINS');
  console.log('   Tool: graph.find_attack_chains');
  console.log('   Command: await mcp.callTool("graph.find_attack_chains", {');
  console.log('     startNodeId: "finding:123",');
  console.log('     maxDepth: 3');
  console.log('   });');
  console.log('   Purpose: Identify sequences of related findings (attack paths)');
  console.log('   What it does:');
  console.log('   - Finds paths through the graph');
  console.log('   - Identifies sequences of related findings');
  console.log('   - Shows potential attack progression');
  console.log('   - Calculates path weights');
  console.log('   Returns: Attack chains with paths and weights\n');
  
  // Complete Workflow
  console.log('='.repeat(70));
  console.log('\n📝 COMPLETE WORKFLOW EXAMPLE\n');
  
  const completeCode = `
// Complete Graph Analysis Workflow
async function analyzeGraph() {
  // 1. Initialize
  const init = await mcp.callTool('graph.init', {});
  console.log('✅', init.data.message);
  
  // 2. Get statistics
  const stats = await mcp.callTool('graph.statistics', {});
  console.log('📊 Graph Stats:', {
    nodes: stats.data.statistics.total_nodes,
    edges: stats.data.statistics.total_edges,
    findings: stats.data.statistics.finding_nodes,
    targets: stats.data.statistics.target_nodes
  });
  
  // 3. Extract patterns
  const patterns = await mcp.callTool('graph.extract_patterns', {});
  console.log('🔍 Patterns found:', patterns.data.count);
  patterns.data.patterns.forEach(([key, pattern]) => {
    console.log(\`  - \${key}: \${pattern.count} findings\`);
  });
  
  // 4. Cluster findings
  const clusters = await mcp.callTool('graph.cluster_findings', {
    minClusterSize: 2
  });
  console.log('🎯 Clusters found:', clusters.data.count);
  clusters.data.clusters.forEach(cluster => {
    console.log(\`  - Cluster \${cluster.id}: \${cluster.nodes.length} findings, similarity: \${cluster.similarity_score.toFixed(2)}\`);
  });
  
  // 5. Find similar findings (for each finding)
  const findings = await mcp.callTool('db.get_findings', { limit: 5 });
  for (const finding of findings.data.findings) {
    const similar = await mcp.callTool('graph.find_similar_findings', {
      findingId: parseInt(finding.id),
      threshold: 0.6
    });
    if (similar.data.count > 0) {
      console.log(\`🔗 Finding #\${finding.id} has \${similar.data.count} similar findings\`);
    }
  }
  
  // 6. Detect graph patterns
  const graphPatterns = await mcp.callTool('graph.detect_patterns', {
    nodeType: 'finding',
    minOccurrences: 3
  });
  console.log('🎨 Graph patterns:', graphPatterns.data.count);
  
  // 7. Find related nodes (for a specific finding)
  if (findings.data.findings.length > 0) {
    const firstFinding = findings.data.findings[0];
    const related = await mcp.callTool('graph.find_related', {
      nodeId: \`finding:\${firstFinding.id}\`,
      maxDepth: 2
    });
    console.log(\`🔗 Nodes related to Finding #\${firstFinding.id}: \${related.data.count}\`);
  }
  
  // 8. Find attack chains
  if (findings.data.findings.length > 0) {
    const firstFinding = findings.data.findings[0];
    const chains = await mcp.callTool('graph.find_attack_chains', {
      startNodeId: \`finding:\${firstFinding.id}\`,
      maxDepth: 3
    });
    console.log(\`⚡ Attack chains from Finding #\${firstFinding.id}: \${chains.data.count}\`);
  }
  
  return {
    statistics: stats.data.statistics,
    patterns: patterns.data.patterns,
    clusters: clusters.data.clusters,
    graphPatterns: graphPatterns.data.patterns
  };
}

// Run the analysis
analyzeGraph().then(results => {
  console.log('\\n✅ Analysis complete!');
  console.log('Results:', results);
});
`;
  
  console.log(completeCode);
  
  console.log('\n' + '='.repeat(70));
  console.log('\n💡 KEY INSIGHTS YOU CAN GET:\n');
  console.log('1. 📊 Overall Statistics - How much data you have');
  console.log('2. 🔍 Vulnerability Patterns - Most common issues');
  console.log('3. 🎯 Finding Clusters - Groups of related findings');
  console.log('4. 🔗 Similar Findings - Related vulnerabilities');
  console.log('5. 🎨 Graph Patterns - Structural patterns');
  console.log('6. 🌐 Relationship Networks - How findings connect');
  console.log('7. ⚡ Attack Chains - Potential attack paths');
  console.log('\n✅ All tools are ready to use in your MCP client!\n');
}

// Run the demonstration
if (require.main === module) {
  completeGraphWorkflow().catch(console.error);
}

module.exports = { completeGraphWorkflow };







