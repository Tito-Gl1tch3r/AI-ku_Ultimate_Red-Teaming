/**
 * Web Worker for File Analysis
 *
 * This worker performs CPU-intensive file analysis operations in the background,
 * preventing the main thread from blocking. It handles:
 * - WASM module initialization
 * - File type detection using Magika
 * - Entropy calculations
 * - String extraction
 * - Hash generation
 * - Pattern matching (IPs, URLs)
 *
 * @module workers/worker
 */

import { Severity, TaskStatus } from "@/types/types";
import getContentType from "@/utils/content-types";
import init, {
  calculate_entropy,
  analyze_file,
  extract_strings,
  calculate_entropy_by_chunks,
  extract_ips,
  extract_urls,
  md5,
  sha1,
  sha256,
  analyze_encrypted_file,
} from "infectio-wasm";
import { Magika } from "magika";

const magika = new Magika();

let initialized = false;

/**
 * Message structure for worker communication.
 */
interface AnalyzeFileMessage {
  /** The task type to perform */
  task: string;
  /** The file to analyze */
  file: File;
  /** Optional password for encrypted files */
  password?: string;
}

/**
 * Main message handler for the worker.
 *
 * Processes incoming messages from the main thread and performs the requested
 * analysis tasks. Results are posted back to the main thread via postMessage.
 *
 * Supported tasks:
 * - `calculate_entropy_by_chunks`: Calculate entropy for file chunks
 * - `analyze_file`: Perform comprehensive file analysis
 *
 * @param e - Message event containing task details
 */
onmessage = async (e: MessageEvent<AnalyzeFileMessage>) => {
  const { task, file, password } = e.data;

  const fileData = new Uint8Array(await file.arrayBuffer());

  if (!initialized) {
    await init();
    await magika.load();
    initialized = true;
  }

  switch (task) {
    case "calculate_entropy_by_chunks":
      new Promise(() => {
        const entropyByChunk = calculate_entropy_by_chunks(fileData, 256);
        postMessage({
          task: task,
          result: entropyByChunk.map((e) => e.entropy),
          status: TaskStatus.Completed,
        });
      });
      break;

    case "analyze_file":
      new Promise(() => {
        const entropy = calculate_entropy(fileData);
        postMessage({
          task: "entropy",
          result: entropy,
          status: TaskStatus.Completed,
        });
      });

      magika.identifyBytes(fileData).then((result) => {
        const contentType = getContentType(result.label);

        if (contentType.mime_type != file.type) {
          postMessage({
            task: "heuristic",
            result: {
              name: "Content type mismatch",
              severity: Severity.Medium,
            },
            status: TaskStatus.Completed,
          });
        }

        postMessage({
          task: "contentType",
          result: contentType,
          status: TaskStatus.Completed,
        });

        postMessage({
          task: "metadata",
          result: [
            {
              title: "Mime Type",
              value: contentType.mime_type,
            },
            {
              title: "Description",
              value: contentType.description,
            },
            {
              title: "Is Text",
              value: contentType.is_text,
            },
            {
              title: "Group",
              value: contentType.group,
            },
          ],
          status: TaskStatus.Completed,
        });
        try {
          const report = password
            ? analyze_encrypted_file(
                fileData,
                contentType.mime_type || "unknown",
                password
              )
            : analyze_file(fileData, contentType.mime_type || "unknown");
          postMessage({ task, result: report, status: TaskStatus.Completed });
        } catch (e) {
          console.error("Failed to analyze file", e);
          postMessage({ task, status: TaskStatus.Failed });
        }
      });

      new Promise(() => {
        const strings = extract_strings(fileData, 5);
        postMessage({
          task: "strings",
          result: strings,
          status: TaskStatus.Completed,
        });

        new Promise(() => {
          const ips = extract_ips(strings);
          postMessage({
            task: "ips",
            result: ips,
            status: TaskStatus.Completed,
          });
        });

        new Promise(() => {
          const urls = extract_urls(strings);
          postMessage({
            task: "urls",
            result: urls,
            status: TaskStatus.Completed,
          });
        });
      });

      new Promise(() => {
        const entropies = calculate_entropy_by_chunks(fileData, 256);
        postMessage({
          task: "entropies",
          result: entropies.map((e) => e.entropy),
          status: TaskStatus.Completed,
        });
      });

      new Promise(() => {
        const md5Hash = md5(fileData);
        postMessage({
          task: "metadata",
          result: {
            title: "MD5",
            value: md5Hash,
          },
          status: TaskStatus.Completed,
        });
        const sha1Hash = sha1(fileData);
        postMessage({
          task: "metadata",
          result: {
            title: "SHA1",
            value: sha1Hash,
          },
          status: TaskStatus.Completed,
        });
        const sha256Hash = sha256(fileData);
        postMessage({
          task: "metadata",
          result: {
            title: "SHA256",
            value: sha256Hash,
          },
          status: TaskStatus.Completed,
        });
      });
      break;

    default:
      postMessage({ task, status: TaskStatus.Failed, error: "Unknown task" });
      break;
  }
};
