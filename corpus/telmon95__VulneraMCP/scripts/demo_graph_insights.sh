#!/bin/bash

# Demo script showing how to get graph insights
# This demonstrates the MCP tool calls you would make

echo "🔍 Graph Insights Demo"
echo "===================="
echo ""
echo "This script shows example MCP tool calls for getting graph insights."
echo "In practice, you'd use these through your MCP client (Cursor, Claude Desktop, etc.)"
echo ""
echo "1. Initialize Graph:"
echo "   mcp.callTool('graph.init', {})"
echo ""
echo "2. Get Statistics:"
echo "   mcp.callTool('graph.statistics', {})"
echo ""
echo "3. Extract Patterns:"
echo "   mcp.callTool('graph.extract_patterns', {})"
echo ""
echo "4. Find Similar Findings:"
echo "   mcp.callTool('graph.find_similar_findings', {"
echo "     findingId: 123,"
echo "     threshold: 0.6"
echo "   })"
echo ""
echo "5. Cluster Findings:"
echo "   mcp.callTool('graph.cluster_findings', {"
echo "     minClusterSize: 2"
echo "   })"
echo ""
echo "6. Detect Patterns:"
echo "   mcp.callTool('graph.detect_patterns', {"
echo "     nodeType: 'finding',"
echo "     minOccurrences: 3"
echo "   })"
echo ""
echo "7. Find Related Nodes:"
echo "   mcp.callTool('graph.find_related', {"
echo "     nodeId: 'finding:123',"
echo "     maxDepth: 2"
echo "   })"
echo ""
echo "8. Find Attack Chains:"
echo "   mcp.callTool('graph.find_attack_chains', {"
echo "     startNodeId: 'finding:123',"
echo "     maxDepth: 3"
echo "   })"
echo ""
echo "For complete examples, see:"
echo "  - GRAPH_INSIGHTS_GUIDE.md"
echo "  - examples/graph_insights_example.js"







