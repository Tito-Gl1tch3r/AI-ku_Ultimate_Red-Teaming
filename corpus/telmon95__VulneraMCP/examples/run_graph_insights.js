#!/usr/bin/env node

/**
 * Interactive Graph Insights Example
 * 
 * This demonstrates how to use graph analysis tools through MCP
 * Note: This requires MCP server to be running
 */

const readline = require('readline');

// Simulated MCP tool calls (in practice, these would be real MCP calls)
const mockMCPTools = {
  'graph.init': async () => ({
    success: true,
    data: { message: 'Graph tables initialized successfully' }
  }),
  
  'graph.statistics': async () => ({
    success: true,
    data: {
      statistics: {
        total_nodes: 150,
        total_edges: 300,
        node_types: 8,
        edge_types: 6,
        finding_nodes: 50,
        target_nodes: 20
      }
    }
  }),
  
  'graph.extract_patterns': async () => ({
    success: true,
    data: {
      patterns: [
        ['type:XSS', {
          type: 'vulnerability_type',
          vulnerability_type: 'XSS',
          count: 15,
          targets: ['https://example.com/api', 'https://example.com/user'],
          common_payloads: ['<script>alert(1)</script>', '<img src=x onerror=alert(1)>'],
          common_endpoints: ['/api/user', '/api/search'],
          severity_distribution: { high: 10, medium: 5 }
        }],
        ['type:SQLi', {
          type: 'vulnerability_type',
          vulnerability_type: 'SQLi',
          count: 8,
          targets: ['https://example.com/search'],
          common_payloads: ["' OR '1'='1", "admin'--"],
          common_endpoints: ['/api/search', '/api/filter'],
          severity_distribution: { critical: 3, high: 5 }
        }]
      ],
      count: 2
    }
  }),
  
  'graph.cluster_findings': async () => ({
    success: true,
    data: {
      clusters: [
        {
          id: 'cluster:123',
          type: 'finding_cluster',
          nodes: ['finding:123', 'finding:124', 'finding:125'],
          similarity_score: 0.82,
          common_properties: {
            type: 'XSS',
            severity: 'high',
            avg_similarity: 0.82
          }
        },
        {
          id: 'cluster:126',
          type: 'finding_cluster',
          nodes: ['finding:126', 'finding:127'],
          similarity_score: 0.75,
          common_properties: {
            type: 'SQLi',
            severity: 'critical',
            avg_similarity: 0.75
          }
        }
      ],
      count: 2
    }
  }),
  
  'graph.find_similar_findings': async (params) => ({
    success: true,
    data: {
      finding: { id: params.findingId, type: 'XSS', severity: 'high' },
      similar: [
        {
          finding: { id: 124, type: 'XSS', severity: 'high' },
          similarity: 0.85,
          reasons: ['same_vulnerability_type', 'similar_target', 'similar_payload']
        },
        {
          finding: { id: 125, type: 'XSS', severity: 'high' },
          similarity: 0.78,
          reasons: ['same_vulnerability_type', 'similar_payload']
        }
      ],
      count: 2
    }
  }),
  
  'graph.detect_patterns': async () => ({
    success: true,
    data: {
      patterns: [
        {
          pattern_id: 'pattern:type:XSS',
          pattern_type: 'common_type',
          matches: [
            { node_id: 'finding:123', node_type: 'finding', confidence: 1.0, details: { type: 'XSS' } },
            { node_id: 'finding:124', node_type: 'finding', confidence: 1.0, details: { type: 'XSS' } }
          ],
          confidence: 0.8
        }
      ],
      count: 1
    }
  })
};

async function runGraphInsightsDemo() {
  console.log('🔍 Graph Insights Demo - Running Example\n');
  console.log('='.repeat(70));
  
  // Step 1: Initialize
  console.log('\n📊 Step 1: Initializing Graph...');
  const initResult = await mockMCPTools['graph.init']();
  console.log('   ✅', initResult.data.message);
  
  // Step 2: Get Statistics
  console.log('\n📈 Step 2: Getting Graph Statistics...');
  const stats = await mockMCPTools['graph.statistics']();
  console.log('   📊 Graph Statistics:');
  console.log('   ', {
    'Total Nodes': stats.data.statistics.total_nodes,
    'Total Edges': stats.data.statistics.total_edges,
    'Findings': stats.data.statistics.finding_nodes,
    'Targets': stats.data.statistics.target_nodes,
    'Node Types': stats.data.statistics.node_types,
    'Edge Types': stats.data.statistics.edge_types
  });
  
  // Step 3: Extract Patterns
  console.log('\n🔍 Step 3: Extracting Patterns from Findings...');
  const patterns = await mockMCPTools['graph.extract_patterns']();
  console.log(`   ✅ Found ${patterns.data.count} patterns\n`);
  
  patterns.data.patterns.forEach(([key, pattern]) => {
    console.log(`   📌 Pattern: ${key}`);
    console.log(`      Type: ${pattern.vulnerability_type}`);
    console.log(`      Count: ${pattern.count} findings`);
    console.log(`      Common Endpoints: ${pattern.common_endpoints.slice(0, 3).join(', ')}`);
    console.log(`      Common Payloads: ${pattern.common_payloads.slice(0, 2).join(', ')}`);
    console.log(`      Severity: ${JSON.stringify(pattern.severity_distribution)}`);
    console.log('');
  });
  
  // Step 4: Cluster Findings
  console.log('🎯 Step 4: Clustering Findings...');
  const clusters = await mockMCPTools['graph.cluster_findings']();
  console.log(`   ✅ Found ${clusters.data.count} clusters\n`);
  
  clusters.data.clusters.forEach(cluster => {
    console.log(`   📦 Cluster: ${cluster.id}`);
    console.log(`      Size: ${cluster.nodes.length} findings`);
    console.log(`      Similarity Score: ${cluster.similarity_score.toFixed(2)}`);
    console.log(`      Common Type: ${cluster.common_properties.type}`);
    console.log(`      Common Severity: ${cluster.common_properties.severity}`);
    console.log('');
  });
  
  // Step 5: Find Similar Findings
  console.log('🔗 Step 5: Finding Similar Findings...');
  const similar = await mockMCPTools['graph.find_similar_findings']({ findingId: 123, threshold: 0.6 });
  console.log(`   ✅ Found ${similar.data.count} similar findings for Finding #123\n`);
  
  similar.data.similar.forEach(s => {
    console.log(`   🔍 Finding #${s.finding.id}:`);
    console.log(`      Similarity: ${(s.similarity * 100).toFixed(0)}%`);
    console.log(`      Reasons: ${s.reasons.join(', ')}`);
    console.log('');
  });
  
  // Step 6: Detect Graph Patterns
  console.log('🎨 Step 6: Detecting Graph Patterns...');
  const graphPatterns = await mockMCPTools['graph.detect_patterns']();
  console.log(`   ✅ Found ${graphPatterns.data.count} graph patterns\n`);
  
  graphPatterns.data.patterns.forEach(pattern => {
    console.log(`   🎯 Pattern: ${pattern.pattern_id}`);
    console.log(`      Type: ${pattern.pattern_type}`);
    console.log(`      Matches: ${pattern.matches.length} nodes`);
    console.log(`      Confidence: ${(pattern.confidence * 100).toFixed(0)}%`);
    console.log('');
  });
  
  // Summary
  console.log('='.repeat(70));
  console.log('\n✅ Graph Insights Demo Complete!\n');
  console.log('📊 Summary:');
  console.log(`   - ${stats.data.statistics.total_nodes} total nodes`);
  console.log(`   - ${stats.data.statistics.total_edges} total edges`);
  console.log(`   - ${patterns.data.count} vulnerability patterns`);
  console.log(`   - ${clusters.data.count} finding clusters`);
  console.log(`   - ${graphPatterns.data.count} graph patterns`);
  console.log('\n💡 Key Insights:');
  console.log('   - XSS is the most common vulnerability type');
  console.log('   - Multiple findings cluster together by similarity');
  console.log('   - Common endpoints and payloads identified');
  console.log('   - Attack patterns can be detected in the graph structure');
  console.log('\n📚 For real usage, use these MCP tools:');
  console.log('   - graph.init');
  console.log('   - graph.statistics');
  console.log('   - graph.extract_patterns');
  console.log('   - graph.cluster_findings');
  console.log('   - graph.find_similar_findings');
  console.log('   - graph.detect_patterns');
  console.log('\n');
}

// Run the demo
if (require.main === module) {
  runGraphInsightsDemo().catch(console.error);
}

module.exports = { runGraphInsightsDemo };







