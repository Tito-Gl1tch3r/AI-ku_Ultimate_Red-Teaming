import React from "react";
import {
  Table as RVTable,
  TableProps as RVTableProps,
  Column,
  AutoSizer,
  TableCellRenderer,
} from "react-virtualized";
import { FaSearch } from "react-icons/fa";

export interface ColumnConfig<T> {
  label: string;
  dataKey: keyof T;
  width?: number;
  cellRenderer?: TableCellRenderer;
}

interface TableProps<T> {
  data: T[];
  columns: ColumnConfig<T>[];
  searchKeys?: (keyof T)[];
  search?: boolean;
  onRowClick?: (row: T) => void;
}

const Table = <T extends Record<string, any>>({
  data,
  columns,
  searchKeys,
  search = true,
  onRowClick,
}: TableProps<T>) => {
  const [searchTerm, setSearchTerm] = React.useState("");

  const filteredData =
    search && searchKeys
      ? data.filter((item) =>
          searchKeys.some((key) =>
            String(item[key]).toLowerCase().includes(searchTerm.toLowerCase())
          )
        )
      : data;

  return (
    <>
      {search && (
        <div className="relative w-full">
          <FaSearch className="absolute left-3 top-3 text-gray-500" />
          <input
            type="text"
            placeholder={`Search in ${data.length} records...`}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10 w-full pr-4 py-2 border border-gray-300 rounded-tl-lg rounded-tr-lg  shadow focus:outline-none"
          />
        </div>
      )}
      <div
        className={`w-full border border-gray-300 rounded-bl-lg rounded-br-lg shadow-lg overflow-hidden ${
          !search && "rounded-t-lg"
        }`}
        style={{
          height: Math.min(filteredData.length, 5) * 40 + 50,
        }}
      >
        <AutoSizer>
          {({ width, height }) => (
            <RVTable
              width={width}
              height={height}
              headerHeight={50}
              rowHeight={40}
              rowCount={filteredData.length}
              rowGetter={({ index }) => filteredData[index]}
              headerClassName="normal-case"
              rowClassName={({ index }) =>
                index % 2 === 0 ? "bg-gray-100" : "bg-white"
              }
              onRowClick={({ rowData }) => onRowClick && onRowClick(rowData)}
            >
              {columns.map((column) => (
                <Column
                  key={column.dataKey as string}
                  width={column.width || width}
                  label={column.label}
                  dataKey={column.dataKey as string}
                  cellRenderer={column.cellRenderer}
                />
              ))}
            </RVTable>
          )}
        </AutoSizer>
      </div>
    </>
  );
};

export default Table;
