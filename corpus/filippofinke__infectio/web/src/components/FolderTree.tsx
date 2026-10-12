import { formatFileSize } from "@/utils/display";
import React, { useState } from "react";
import {
  FaFolder,
  FaFolderOpen,
  FaFileAlt,
  FaChevronDown,
  FaChevronUp,
  FaDownload,
  FaExternalLinkAlt,
  FaChartBar,
  FaLock,
} from "react-icons/fa";

interface Item {
  name: string;
  item_type: "file" | "directory";
  size: number;
  data: Uint8Array;
  encrypted: boolean;
}

interface TreeNode {
  name: string;
  children: TreeNode[];
  isDirectory: boolean;
  size: number;
  data?: Uint8Array;
  encrypted: boolean;
}

interface FolderTreeProps {
  items: Item[];
  onScanFile?: (file: File) => void;
  onShowEntropy?: (file: File) => void;
}

const buildTree = (items: Item[]): TreeNode[] => {
  const root: TreeNode[] = [];

  const addToTree = (node: TreeNode[], pathParts: string[], item: Item) => {
    const part = pathParts.shift();
    if (!part) return;

    let childNode = node.find((child) => child.name === part);

    if (!childNode) {
      childNode = {
        encrypted: item.encrypted,
        name: part,
        children: [],
        isDirectory: pathParts.length > 0 || item.item_type === "directory",
        size: item.size,
      };
      node.push(childNode);
    }

    if (pathParts.length > 0) {
      addToTree(childNode.children, pathParts, item);
    } else if (item.item_type === "file") {
      // Add file data when it's a file
      childNode.data = item.data;
    }
  };

  items.forEach((item) => {
    const parts = item.name.split("/").filter(Boolean);
    addToTree(root, parts, item);
  });

  return root;
};

const FolderTree: React.FC<FolderTreeProps> = ({
  items,
  onScanFile,
  onShowEntropy,
}) => {
  const [expanded, setExpanded] = useState<{ [key: string]: boolean }>({});

  const toggleNode = (path: string) => {
    setExpanded((prev) => ({ ...prev, [path]: !prev[path] }));
  };

  const downloadFile = (fileName: string, data: Uint8Array) => {
    data = new Uint8Array(data);
    const blob = new Blob([data], { type: "application/octet-stream" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const renderTree = (nodes: TreeNode[], parentPath = "") => {
    return nodes.map((node, index) => {
      const currentPath = `${parentPath}/${node.name}`;

      return (
        <div
          key={currentPath}
          className={`${parentPath != "" && "pl-4"} w-full`}
        >
          {node.isDirectory ? (
            <div className="w-full">
              <div
                className="cursor-pointer flex items-center justify-between w-full rounded-lg border border-gray-200 bg-white p-2"
                onClick={() => toggleNode(currentPath)}
              >
                <div className="flex items-center">
                  <span className="mr-2">
                    {expanded[currentPath] ? <FaFolderOpen /> : <FaFolder />}
                  </span>
                  {node.name}/
                </div>
                <span>
                  {expanded[currentPath] ? <FaChevronUp /> : <FaChevronDown />}
                </span>
              </div>
              {expanded[currentPath] && (
                <div className="pl-4">
                  {renderTree(node.children, currentPath)}
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center w-full rounded-lg border border-gray-200 bg-white p-2">
              <span className="mr-2">
                <FaFileAlt />
              </span>
              {node.name}{" "}
              <span className="ml-2 text-xs text-gray-500">
                ({formatFileSize(node.size)})
              </span>
              {node.data && !node.encrypted && (
                <div className="ml-auto flex items-center">
                  {onShowEntropy && (
                    <button
                      className="text-blue-500 hover:text-blue-700 mr-2"
                      onClick={() => {
                        let file = new File(
                          [new Uint8Array(node.data!)],
                          node.name
                        );
                        onShowEntropy(file);
                      }}
                      title="Show entropy"
                    >
                      <FaChartBar />
                    </button>
                  )}
                  {onScanFile && (
                    <button
                      className="text-blue-500 hover:text-blue-700 mr-2"
                      onClick={() => {
                        let file = new File(
                          [new Uint8Array(node.data!)],
                          node.name
                        );
                        onScanFile(file);
                      }}
                      title="Scan file"
                    >
                      <FaExternalLinkAlt />
                    </button>
                  )}
                  <button
                    title="Download file"
                    className="text-blue-500 hover:text-blue-700"
                    onClick={() => downloadFile(node.name, node.data!)}
                  >
                    <FaDownload />
                  </button>
                </div>
              )}
              {node.encrypted && (
                <div className="ml-auto flex items-center">
                  <span className="text-xs text-red-500">Encrypted</span>
                  <FaLock className="text-red-500 ml-1" />
                </div>
              )}
            </div>
          )}
        </div>
      );
    });
  };

  if (items.length === 0) {
    return null;
  }

  const tree = buildTree(items);

  return (
    <div className="bg-white p-4 rounded-lg border border-gray-300 w-full">
      {renderTree(tree)}
    </div>
  );
};

export default FolderTree;
