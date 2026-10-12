import React, { useState } from "react";
import Table, { ColumnConfig } from "./Table";
import { FaChevronRight, FaInfoCircle, FaRobot } from "react-icons/fa";
import { useLLM } from "@/contexts/useLLM";

interface ImportsProps {
  imports: Map<string, string[]>;
}

interface ImportData {
  module: string;
  importsCount: number;
}

interface FunctionData {
  function: string;
}

const Imports = ({ imports }: ImportsProps) => {
  const { sendMessage, isReady, setShowChat } = useLLM();
  const [selectedModule, setSelectedModule] = useState<string | null>(null);

  let data: ImportData[] = [];
  imports.forEach((importsList, module) => {
    data.push({
      module,
      importsCount: importsList.length,
    });
  });

  data = data.sort((a, b) => b.importsCount - a.importsCount);

  let columns: ColumnConfig<ImportData>[] = [
    {
      label: "Module",
      dataKey: "module" as keyof ImportData,
      cellRenderer: (data) => (
        <div
          className={
            "flex cursor-pointer " +
            (selectedModule === data.cellData ? "text-blue-500 font-bold" : "")
          }
        >
          {data.cellData}
        </div>
      ),
    },
    {
      label: "Imports Count",
      dataKey: "importsCount" as keyof ImportData,
      width: 150,
      cellRenderer: (data) => (
        <div className="flex items-center justify-between cursor-pointer">
          {data.cellData}

          <FaChevronRight className="inline ml-2" />
        </div>
      ),
    },
  ];

  if (selectedModule) {
    columns.pop();
  }

  const handleRowClick = (row: ImportData) => {
    if (selectedModule === row.module) setSelectedModule(null);
    else setSelectedModule(row.module);
  };

  const selectedFunctions =
    (selectedModule && imports.get(selectedModule)) || [];

  const functionsColumns: ColumnConfig<FunctionData>[] = [
    {
      label: "Function",
      dataKey: "function" as keyof FunctionData,
      cellRenderer: (data) => (
        <div className="flex items-center justify-between">
          <span className="mr-2">{data.cellData}</span>
          {isReady && (
            <FaInfoCircle
              className="cursor-pointer text-blue-600"
              onClick={() => {
                sendMessage(
                  `Briefly summarize the function "${data.cellData}" from the module "${selectedModule}". Be short and concise.`
                );
                setShowChat(true);
              }}
            />
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="flex w-full">
      <div className="flex-grow">
        <Table
          data={data}
          columns={columns}
          searchKeys={["module"]}
          onRowClick={handleRowClick}
        />
      </div>
      {selectedModule && (
        <div className="flex-grow">
          <Table
            data={selectedFunctions.map((func) => ({ function: func }))}
            columns={functionsColumns}
            searchKeys={["function"]}
          />
        </div>
      )}
    </div>
  );
};

export default Imports;
