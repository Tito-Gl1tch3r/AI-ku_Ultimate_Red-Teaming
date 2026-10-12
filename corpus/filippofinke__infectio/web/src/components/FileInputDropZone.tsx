import React, { useCallback, useRef, useState } from "react";
import { FaUpload } from "react-icons/fa";

interface FileInputDropZoneProps {
  onFileDrop: (file: File) => void;
}

export default function FileInputDropZone({
  onFileDrop,
}: FileInputDropZoneProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      setIsDragging(false);
      const files = event.dataTransfer.files;
      if (files.length > 0) {
        onFileDrop(files[0]);
      }
    },
    [onFileDrop]
  );

  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files && files.length > 0) {
      onFileDrop(files[0]);
    }
  };

  return (
    <div
      className={`flex flex-col items-center justify-center w-full h-64 border-2 border-dashed rounded-lg transition-all duration-300 ease-in-out ${
        isDragging
          ? "border-blue-500 bg-blue-50"
          : "border-gray-300 hover:border-blue-500 hover:bg-gray-50"
      }`}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onClick={() => fileInputRef.current?.click()}
    >
      <input
        type="file"
        ref={fileInputRef}
        className="hidden"
        onChange={handleFileChange}
      />
      <div className="flex flex-col items-center justify-center space-y-4">
        <div
          className={`p-4 rounded-full bg-blue-100 transition-all duration-300 ease-in-out ${
            isDragging ? "scale-110" : "scale-100"
          }`}
        >
          <FaUpload className="text-blue-500" size={32} strokeWidth={1.5} />
        </div>
        <div className="text-center">
          <p className="text-lg font-semibold text-gray-700">
            {isDragging ? "Drop your file here" : "Drag & Drop your file here"}
          </p>
          <p className="text-sm text-gray-500 mt-1">or click to browse</p>
        </div>
      </div>
    </div>
  );
}
