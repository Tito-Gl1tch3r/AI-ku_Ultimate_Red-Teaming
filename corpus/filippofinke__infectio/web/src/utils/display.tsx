import { Severity, TaskStatus } from "@/types/types";
import React from "react";

import {
  FaCheckCircle,
  FaFileAlt,
  FaFileArchive,
  FaFileAudio,
  FaFileCode,
  FaFileContract,
  FaFileCsv,
  FaFileDownload,
  FaFileExcel,
  FaFileExport,
  FaFileImage,
  FaFileImport,
  FaFileInvoice,
  FaFileInvoiceDollar,
  FaFileMedical,
  FaFileMedicalAlt,
  FaFilePdf,
  FaFilePowerpoint,
  FaFilePrescription,
  FaFileSignature,
  FaFileUpload,
  FaFileVideo,
  FaFileWord,
  FaSpinner,
  FaTimesCircle,
} from "react-icons/fa";

export const formatFileSize = (size: number): string => {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let unitIndex = 0;
  let fileSize = size;
  while (fileSize >= 1024 && unitIndex < units.length - 1) {
    fileSize /= 1024;
    unitIndex++;
  }
  return `${fileSize.toFixed(1)} ${units[unitIndex]}`;
};

export const getFileIcon = (file: File) => {
  const mimeType = file.type;

  switch (mimeType) {
    case "application/pdf":
      return <FaFilePdf className="text-gray-400" />;
    case "application/msword":
    case "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
      return <FaFileWord className="text-gray-400" />;
    case "application/vnd.ms-excel":
    case "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
      return <FaFileExcel className="text-gray-400" />;
    case "application/vnd.ms-powerpoint":
    case "application/vnd.openxmlformats-officedocument.presentationml.presentation":
      return <FaFilePowerpoint className="text-gray-400" />;
    case "application/zip":
    case "application/x-7z-compressed":
    case "application/x-rar-compressed":
    case "application/x-tar":
      return <FaFileArchive className="text-gray-400" />;
    case "text/csv":
      return <FaFileCsv className="text-gray-400" />;
    case "text/plain":
    case "text/html":
    case "application/javascript":
    case "application/json":
    case "text/xml":
      return <FaFileCode className="text-gray-400" />;
    case "image/jpeg":
    case "image/png":
    case "image/gif":
    case "image/svg+xml":
      return <FaFileImage className="text-gray-400" />;
    case "video/mp4":
    case "video/x-matroska":
    case "video/webm":
    case "video/quicktime":
      return <FaFileVideo className="text-gray-400" />;
    case "audio/mpeg":
    case "audio/wav":
    case "audio/ogg":
      return <FaFileAudio className="text-gray-400" />;
    case "application/vnd.openxmlformats-officedocument.spreadsheetml.template":
      return <FaFileExport className="text-gray-400" />;
    case "application/vnd.openxmlformats-officedocument.presentationml.template":
      return <FaFileImport className="text-gray-400" />;
    case "application/vnd.ms-excel.sheet.macroenabled.12":
      return <FaFileContract className="text-gray-400" />;
    case "application/vnd.openxmlformats-officedocument.wordprocessingml.template":
      return <FaFileSignature className="text-gray-400" />;
    case "application/vnd.openxmlformats-officedocument.presentationml.slideshow":
      return <FaFilePrescription className="text-gray-400" />;
    case "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
      return <FaFileInvoice className="text-gray-400" />;
    case "application/vnd.ms-excel.addin.macroenabled.12":
      return <FaFileInvoiceDollar className="text-gray-400" />;
    case "application/x-msdownload":
      return <FaFileDownload className="text-gray-400" />;
    case "application/vnd.oasis.opendocument.spreadsheet":
      return <FaFileMedical className="text-gray-400" />;
    case "application/vnd.oasis.opendocument.presentation":
      return <FaFileMedicalAlt className="text-gray-400" />;
    case "application/vnd.oasis.opendocument.text":
      return <FaFileUpload className="text-gray-400" />;
    default:
      return <FaFileAlt className="text-gray-400" />;
  }
};

export const renderStatusIcon = (status: TaskStatus) => {
  if (status === TaskStatus.Idle) {
    return null;
  }

  if (status === TaskStatus.Pending) {
    return <FaSpinner className="text-blue-500 animate-spin" />;
  }

  if (status === TaskStatus.Completed) {
    return <FaCheckCircle className="text-green-500" />;
  }

  if (status === TaskStatus.Failed) {
    return <FaTimesCircle className="text-red-500" />;
  }
};

export const renderSeverity = (severity: Severity) => {
  const getColor = () => {
    switch (severity) {
      case Severity.Low:
        return "bg-green-500";
      case Severity.Medium:
        return "bg-yellow-500";
      case Severity.High:
        return "bg-red-500";
      case Severity.Info:
        return "bg-blue-500";
      default:
        return "bg-gray-500";
    }
  };

  const getText = () => {
    switch (severity) {
      case Severity.Low:
        return "Regular";
      case Severity.Medium:
        return "Suspicious";
      case Severity.High:
        return "Dangerous";
      case Severity.Info:
        return "Info";
      default:
        return "";
    }
  };

  return (
    <div className="flex items-center">
      <span className={`w-3 h-3 rounded-full ${getColor()} mr-2`}></span>
      <span>{getText()}</span>
    </div>
  );
};
