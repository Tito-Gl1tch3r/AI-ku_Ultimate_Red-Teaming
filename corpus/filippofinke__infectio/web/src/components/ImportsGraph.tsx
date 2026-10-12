import React from "react";
import { GraphCanvas, GraphEdge, GraphNode } from "reagraph";

interface ImportsGraphProps {
  root: string;
  imports: Map<string, string[]>;
}

const ImportsGraph: React.FC<ImportsGraphProps> = ({ root, imports }) => {
  const nodes: GraphNode[] = [];

  nodes.push({
    id: "root",
    label: root,
    fill: "#155582",
  });

  for (const [module, modImports] of imports) {
    nodes.push({
      id: module,
      label: module,
      fill: "#1e79ba",
    });
    for (const importedModule of modImports) {
      nodes.push({
        fill: "#1394f0",
        id: importedModule,
        label: importedModule,
      });
    }
  }

  const edges: GraphEdge[] = [];

  for (const [module, modImports] of imports) {
    edges.push({
      id: `root-${module}`,
      source: "root",
      target: module,
    });

    for (const importedModule of modImports) {
      edges.push({
        id: `${module}-${importedModule}`,
        source: module,
        target: importedModule,
      });
    }
  }

  return (
    <div
      style={{ width: "100%", height: "500px", position: "relative" }}
      className="border border-gray-300 rounded-lg"
    >
      <GraphCanvas nodes={nodes} edges={edges} />
    </div>
  );
};

export default ImportsGraph;
