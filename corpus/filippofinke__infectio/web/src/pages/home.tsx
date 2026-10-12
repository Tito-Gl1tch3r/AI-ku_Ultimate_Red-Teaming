import React, { useEffect, useMemo, useState } from "react";
import ImportsGraph from "../components/ImportsGraph";
import Strings from "../components/Strings";
import FileInputDropZone from "../components/FileInputDropZone";
import InfoBanner from "../components/InfoBanner";
import Logo from "../components/Logo";
import FileInfo from "../components/FileInfo";
import LineChart from "../components/LineChart";
import FolderTree from "../components/FolderTree";
import Ips from "../components/Ips";
import Urls from "../components/Urls";
import Metadata from "../components/Metadata";
import Tabs from "../components/Tabs";
import Imports from "../components/Imports";
import Chat from "../components/Chat";
import CodeAnalysis from "../components/CodeAnalysis";
import { Heuristic, Report, Severity, TaskStatus } from "../types/types";
import { renderStatusIcon } from "../utils/display";
import useDragAndDrop from "../hooks/useDragAndDrop";
import { FaSpinner, FaUpload } from "react-icons/fa";
import Heuristics from "../components/Heuristics";
import Modal from "../components/Modal";

const HomePage = () => {
  const [selectedFile, setSelectedFile] = useState<number>(0);
  const [files, setFiles] = useState<File[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [translateY, setTranslateY] = useState(0);

  const { isDragging } = useDragAndDrop((file) => {
    if (translateY == 0) handleFileChange(file);
  });

  const [showEntropy, setShowEntropy] = useState<number[]>();
  const [password, setPassword] = useState<string>();

  async function handleShowEntropy(file: File) {
    setShowEntropy([]);
    const worker = new Worker(
      new URL("./../workers/worker.ts", import.meta.url)
    );
    worker.onmessage = (e: any) => {
      const { task, result } = e.data;
      switch (task) {
        case "calculate_entropy_by_chunks":
          setShowEntropy(result);
          break;
        default:
          break;
      }
    };

    worker.postMessage({ task: "calculate_entropy_by_chunks", file });
  }

  async function handleFileChange(file: File, password?: string) {
    setFiles((old) => [...old, file]);
    setSelectedFile(files.length);
    setReports((old) => [
      ...old,
      {
        status: {
          entropy: TaskStatus.Pending,
          entropies: TaskStatus.Pending,
          report: TaskStatus.Pending,
          strings: TaskStatus.Pending,
          ips: TaskStatus.Pending,
          urls: TaskStatus.Pending,
        },
        metadata: [],
        entropies: [],
        strings: [],
        ips: [],
        urls: [],
        report: undefined,
        contentType: undefined,
        heuristics: [],
      },
    ]);

    const fileId = files.length;

    const worker = new Worker(
      new URL("./../workers/worker.ts", import.meta.url)
    );
    worker.onmessage = (e: any) => {
      const { task, result, status } = e.data;

      switch (task) {
        case "contentType":
          setReports((old) => {
            const updatedReports = [...old];
            updatedReports[fileId].contentType = result;
            return updatedReports;
          });
          break;
        case "heuristic":
          setReports((old) => {
            const updatedReports = [...old];
            updatedReports[fileId].heuristics = [
              ...updatedReports[fileId].heuristics,
              result,
            ];
            return updatedReports;
          });
          break;
        case "metadata":
          setReports((old) => {
            const updatedReports = [...old];
            updatedReports[fileId].metadata = [
              ...updatedReports[fileId].metadata,
              ...(Array.isArray(result) ? result : [result]),
            ];
            return updatedReports;
          });
          break;
        case "entropy":
          setReports((old) => {
            const updatedReports = [...old];
            updatedReports[fileId].status.entropy = status;
            updatedReports[fileId].metadata = [
              ...updatedReports[fileId].metadata,
              {
                title: "Entropy",
                value: result.toString(),
              },
            ];
            return updatedReports;
          });
          break;
        case "analyze_file":
          setReports((old) => {
            const updatedReports = [...old];
            updatedReports[fileId].status.report = status;
            updatedReports[fileId].report = result;

            if (result && "heuristics" in result && result.heuristics) {
              let heuristics: Heuristic[] = [];
              for (const [key, value] of result.heuristics) {
                heuristics.push({
                  name: key as string,
                  severity: value as Severity,
                });
              }

              updatedReports[fileId].heuristics = [
                ...updatedReports[fileId].heuristics,
                ...heuristics,
              ];
            }

            if (result && "metadata" in result) {
              let metadata = [];
              for (const [key, value] of result.metadata) {
                metadata.push({
                  title: key as string,
                  value: value as string,
                });
              }
              updatedReports[fileId].metadata = [
                ...updatedReports[fileId].metadata,
                ...metadata,
              ];
            }

            return updatedReports;
          });

          break;
        case "strings":
          setReports((old) => {
            const updatedReports = [...old];
            updatedReports[fileId].status.strings = status;
            updatedReports[fileId].strings = result;
            return updatedReports;
          });

          break;
        case "ips":
          setReports((old) => {
            const updatedReports = [...old];
            updatedReports[fileId].status.ips = status;
            updatedReports[fileId].ips = result;
            return updatedReports;
          });
          break;
        case "urls":
          setReports((old) => {
            const updatedReports = [...old];
            updatedReports[fileId].status.urls = status;
            updatedReports[fileId].urls = result;
            return updatedReports;
          });
          break;
        case "entropies":
          setReports((old) => {
            const updatedReports = [...old];
            updatedReports[fileId].status.entropies = status;
            updatedReports[fileId].entropies = result;
            return updatedReports;
          });
          break;
        default:
          break;
      }
    };

    worker.postMessage({ task: "analyze_file", file, password });
  }

  const closeReport = (index: number) => {
    setFiles((old) => old.filter((_, i) => i !== index));
    setReports((old) => old.filter((_, i) => i !== index));
    setSelectedFile(index - 1 >= 0 ? index - 1 : 0);
  };

  useEffect(() => {
    if (files.length === 0) {
      setTranslateY(window.innerHeight / 5);
    } else {
      setTranslateY(0);
    }
  }, [files]);

  const {
    status,
    entropies = [],
    metadata = [],
    strings = [],
    ips = [],
    urls = [],
    report,
    contentType,
    heuristics = [],
  } = useMemo(() => {
    return reports[selectedFile] || {};
  }, [reports, selectedFile]);

  const file = files[selectedFile];

  const analysisComplete = status
    ? Object.values(status).every((s) => s === TaskStatus.Completed)
    : false;

  const tabs = [];

  if (strings.length > 0)
    tabs.push({ label: "Strings", content: <Strings strings={strings} /> });

  if (ips.length > 0) tabs.push({ label: "IPs", content: <Ips ips={ips} /> });

  if (urls.length > 0)
    tabs.push({ label: "URLs", content: <Urls urls={urls} /> });

  const isEncrypted =
    report && report.items && report.items.some((item: any) => item.encrypted);

  return (
    <>
      <Modal
        open={showEntropy !== undefined}
        onClose={() => setShowEntropy(undefined)}
      >
        {showEntropy && showEntropy.length > 0 ? (
          <LineChart
            title="Entropy by chunks"
            labels={showEntropy.map((_, i) => i.toString())}
            dataPoints={showEntropy}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <FaSpinner className="animate-spin mr-1" size={20} />
            Calculating entropy by chunks...
          </div>
        )}
      </Modal>

      {isDragging && files.length > 0 && (
        <div className="fixed inset-0 flex items-center justify-center z-10">
          <div className="bg-gray-100 p-8 rounded-lg shadow-md flex flex-col items-center">
            <div className={`p-4 rounded-full bg-blue-100`}>
              <FaUpload className="text-blue-500" size={32} strokeWidth={1.5} />
            </div>
            <p className="mt-2 text-lg font-semibold text-gray-600">
              Drag & Drop your file to scan
            </p>
          </div>
        </div>
      )}

      <div
        className={`flex justify-center bg-gray-100 transition-transform duration-500`}
        style={{ transform: `translateY(${translateY}px)` }}
      >
        <div className="container mx-auto p-4 flex flex-col items-center space-y-4">
          <div
            className={
              files.length > 0
                ? "flex items-center justify-between w-full space-x-4"
                : ""
            }
          >
            <Logo />
            {files.length > 0 && (
              <div className="flex items-center space-x-4">
                {files.length > 1 && (
                  <select
                    value={selectedFile}
                    onChange={(e) => setSelectedFile(Number(e.target.value))}
                    className="border border-gray-300 rounded px-2 py-1"
                  >
                    {files.map((file, index) => (
                      <option key={index} value={index}>
                        {file.name}
                      </option>
                    ))}
                  </select>
                )}
                <button
                  className="flex items-center space-x-2 text-blue-500"
                  onClick={() => document.getElementById("file-input")?.click()}
                >
                  <span>Scan another file</span>
                </button>
                <input
                  id="file-input"
                  type="file"
                  className="hidden"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      handleFileChange(e.target.files[0]);
                    }
                  }}
                />
              </div>
            )}
          </div>

          {!file && (
            <>
              <InfoBanner
                text="Infectio is a tool for offline malware analysis, developed in WebAssembly."
                linkText="Learn more"
                linkHref="/learn-more"
              />
              <FileInputDropZone onFileDrop={handleFileChange} />
            </>
          )}

          {file && (
            <>
              <FileInfo
                onCancel={() => {
                  closeReport(selectedFile);
                }}
                file={file}
              />
            </>
          )}

          {!analysisComplete && file && (
            <div className="w-full bg-white rounded-lg p-4 border border-gray-300">
              <h3 className="text-lg font-semibold mb-3">Analysis Status</h3>
              <ul className="space-y-2">
                <li className="flex items-center justify-between">
                  <span>Entropy Calculation</span>
                  {renderStatusIcon(status.entropy)}
                </li>
                <li className="flex items-center justify-between">
                  <span>Entropy by Chunks</span>
                  {renderStatusIcon(status.entropies)}
                </li>
                <li className="flex items-center justify-between">
                  <span>File Analysis Report</span>
                  {renderStatusIcon(status.report)}
                </li>
                <li className="flex items-center justify-between">
                  <span>String Extraction</span>
                  {renderStatusIcon(status.strings)}
                </li>
                <li className="flex items-center justify-between">
                  <span>IP Extraction</span>
                  {renderStatusIcon(status.ips)}
                </li>
                <li className="flex items-center justify-between">
                  <span>URL Extraction</span>
                  {renderStatusIcon(status.urls)}
                </li>
              </ul>
            </div>
          )}

          {heuristics.length > 0 && <Heuristics heuristics={heuristics} />}

          {metadata.length > 0 && <Metadata metadata={metadata} />}

          {report && report.items && (
            <>
              {isEncrypted === true && (
                <div className="w-full bg-red-100 rounded-lg p-4 border border-red-300">
                  <h3 className="text-lg font-semibold mb-3">Warning</h3>
                  <p>
                    This file contain encrypted data. Provide a password to
                    decrypt it.
                  </p>
                  <div className="flex flex-row items-center justify-between">
                    <input
                      type="password"
                      className="w-full border border-gray-300 rounded px-4 py-2 mt-4 mr-2"
                      placeholder="Password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                    />

                    <button
                      className="mt-4 bg-red-500 text-white px-4 py-2 rounded-lg"
                      onClick={() => {
                        handleFileChange(file, password);
                        setPassword("");
                      }}
                    >
                      Decrypt
                    </button>
                  </div>
                </div>
              )}

              <FolderTree
                items={report.items}
                onScanFile={handleFileChange}
                onShowEntropy={handleShowEntropy}
              />
            </>
          )}
          <Tabs tabs={tabs} />

          {file &&
            contentType &&
            ["code", "text"].includes(contentType.group || "") && (
              <CodeAnalysis file={file} contentType={contentType} />
            )}
          {report && report.imports && report.imports.size > 0 && file && (
            <>
              <Imports imports={report.imports} />
              <ImportsGraph root={file.name} imports={report.imports} />
            </>
          )}
          {entropies.length > 0 && (
            <LineChart
              title="Entropy by chunks"
              labels={entropies.map((_, i) => i.toString())}
              dataPoints={entropies}
            />
          )}
        </div>
      </div>
    </>
  );
};

export default HomePage;
