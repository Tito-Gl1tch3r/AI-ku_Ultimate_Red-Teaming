import { formatFileSize, getFileIcon } from "@/utils/display";
import React from "react";
import { FaTimes } from "react-icons/fa";

interface FileInfoProps {
  file: File;
  onCancel: () => void;
}

const FileInfo: React.FC<FileInfoProps> = ({ file, onCancel }) => {
  return (
    <div className="flex items-center border border-gray-300 rounded-lg p-4 w-full justify-between bg-white">
      <div className="flex items-center">
        <div className="text-4xl p-4 bg-gray-200 rounded-lg">
          {getFileIcon(file)}
        </div>

        <div className="flex flex-col ml-2">
          <span className="text-lg font-semibold text-gray-700">
            {file.name}
          </span>
          <span className="text-sm text-gray-500">
            {formatFileSize(file.size)} -{" "}
            {new Date(file.lastModified).toLocaleString()}
          </span>
        </div>
      </div>

      <button onClick={onCancel} className="text-gray-500 hover:text-red-500">
        <FaTimes className="text-2xl" />
      </button>
    </div>
  );
};

export default FileInfo;
