import { Constants } from '../config/constants.js';
import { Logger } from '../utils/logger.js';
import { MessageSender } from '../utils/messageSender.js';
import { readMemoryBytes } from '../utils/memoryUtils.js';

/**
 * Class responsible for dumping module data from memory or file system.
 */
export class ModuleDumper {
  private readonly logger: Logger;
  private readonly messageSender: MessageSender;
  private readonly dumpedModules: Set<string>;

  /**
   * Creates a new ModuleDumper instance.
   *
   * @param {Logger} logger - Logger instance for output.
   * @param {MessageSender} messageSender - MessageSender instance for sending data to host.
   */
  constructor(logger: Logger, messageSender: MessageSender) {
    this.logger = logger;
    this.messageSender = messageSender;
    this.dumpedModules = new Set<string>();
  }

  /**
   * Checks if a module has already been dumped.
   *
   * @param {string} moduleName - The module name to check.
   * @returns {boolean} True if the module has been dumped, false otherwise.
   */
  public isModuleDumped(moduleName: string): boolean {
    return this.dumpedModules.has(moduleName);
  }

  /**
   * Gets all dumped module names.
   * Note: Primarily intended for diagnostic and debugging purposes.
   * This method provides visibility into which modules have already been processed,
   * which can be useful for troubleshooting or developing extensions.
   *
   * @returns {Set<string>} Set of all dumped module names.
   */
  public getDumpedModules(): Set<string> {
    return new Set(this.dumpedModules);
  }

  /**
   * Dumps a module, first trying to read from memory. If memory read fails,
   * attempts to read the *entire* file from disk using readAllBytes() as a fallback.
   *
   * @param {object} module - The Frida Module object to dump.
   * @returns {boolean} True if the module was successfully dumped, false otherwise.
   */
  public dumpModule(module: Module): boolean {
    // Basic validation
    if (!module || !module.name || !module.base || typeof module.size !== 'number') {
      this.logger.error(`Invalid module data received: ${JSON.stringify(module)}`);
      return false;
    }

    if (this.dumpedModules.has(module.name)) {
      // Already processed
      return true;
    }

    this.logger.log(
      `Attempting to dump ${module.name} (Base: ${module.base}, Size: ${module.size}, Path: ${
        module.path || 'N/A'
      })`,
    );
    this.dumpedModules.add(module.name); // Mark as processed early to prevent reentry

    try {
      // Send initial module information (always send this)
      this.messageSender.sendModuleInfo(module.name, module.base, module.size, module.path || null);

      // Handle modules with reported size 0 (e.g., some system mappings)
      if (module.size === 0) {
        this.logger.warn(`Module ${module.name} reported size 0. Skipping data dump.`);
        this.messageSender.sendModuleComplete(module.name);
        return true; // Nothing to read
      }

      return this.dumpModuleData(module);
    } catch (error) {
      // Catch any other unexpected errors during the dump process
      this.logger.error(
        `General error during dump of ${module.name}`,
        error instanceof Error ? error : new Error(String(error)),
      );
      this.messageSender.sendModuleError(
        module.name,
        `General dump error: ${error instanceof Error ? error.message : String(error)}`,
      );
      return false;
    }
  }

  /**
   * Internal method to dump the module data from memory or file.
   *
   * @param {object} module - The module to dump.
   * @returns {boolean} True if successful, false otherwise.
   */
  private dumpModuleData(module: Module): boolean {
    let memoryReadOk = true; // Flag to track if memory reading was successful throughout

    // --- Attempt Memory Read First ---
    for (let offset = 0; offset < module.size; offset += Constants.CHUNK_SIZE) {
      const currentChunkSize = Math.min(Constants.CHUNK_SIZE, module.size - offset);
      try {
        // Read chunk from memory
        const currentAddress = module.base.add(offset);
        // Use our utility function to read memory bytes
        const chunkData = readMemoryBytes(currentAddress, currentChunkSize);

        if (!chunkData) {
          throw new Error('Memory read returned null');
        }

        // Send chunk read from memory
        this.messageSender.sendModuleChunk(module.name, offset, chunkData);
      } catch (memError) {
        // Handle memory read error
        this.logger.warn(
          `Memory read failed for ${module.name} at offset ${offset}: ${
            memError instanceof Error ? memError.message : String(memError)
          }. Checking file fallback...`,
        );
        memoryReadOk = false; // Mark memory read as failed

        // --- Attempt Fallback to Reading Entire File ---
        if (module.path && module.path.length > 0) {
          return this.dumpFromFile(module);
        } else {
          // Memory read failed, and NO file path is available
          this.logger.error(
            `Memory read failed for ${module.name} at offset ${offset} (${
              memError instanceof Error ? memError.message : String(memError)
            }), no file path.`,
          );
          this.messageSender.sendModuleError(
            module.name,
            `Memory read failed at offset ${offset}: ${
              memError instanceof Error ? memError.message : String(memError)
            }. No file path for fallback.`,
          );
          return false; // Stop dumping this module
        }
      }
    }

    // If the memory read loop completed without any errors
    if (memoryReadOk) {
      this.logger.log(`Finished sending chunks for ${module.name} (via memory)`);
      this.messageSender.sendModuleComplete(module.name);
      return true;
    }

    return false;
  }

  /**
   * Attempts to dump a module by reading it from disk.
   *
   * @param {object} module - The module to dump from its file path.
   * @returns {boolean} True if successful, false otherwise.
   */
  private dumpFromFile(module: Module): boolean {
    this.logger.log(`Path found: ${module.path}. Attempting full file read fallback...`);
    try {
      // Open file, read all bytes, close immediately
      this.logger.log(`Reading all bytes from file ${module.path}...`);
      const fileData = File.readAllBytes(module.path || ''); // Use logical OR instead of non-null assertion

      if (!fileData || fileData.byteLength === 0) {
        throw new Error('readAllBytes() returned empty or null data.');
      }

      this.logger.log(
        `Successfully read ${fileData.byteLength} bytes from file. Sending chunks from file data...`,
      );

      // --- Send ALL chunks from the file data ---
      for (
        let fileOffset = 0;
        fileOffset < fileData.byteLength;
        fileOffset += Constants.CHUNK_SIZE
      ) {
        const fileChunkSize = Math.min(Constants.CHUNK_SIZE, fileData.byteLength - fileOffset);
        // Slice the ArrayBuffer containing the full file data
        const fileChunkData = fileData.slice(fileOffset, fileOffset + fileChunkSize);

        // Send the chunk derived from the file
        this.messageSender.sendModuleChunk(
          module.name,
          fileOffset, // Use the offset within the file data
          fileChunkData,
        );
      }

      this.logger.log(`Finished sending chunks from file ${module.name}`);
      // Mark as complete after successfully sending all file chunks
      this.messageSender.sendModuleComplete(module.name);
      return true;
    } catch (fileError) {
      // Handle errors during file operations
      const errMsg = fileError instanceof Error ? fileError.message : String(fileError);
      this.logger.error(`Full file read fallback failed for ${module.name}: ${errMsg}`);
      this.messageSender.sendModuleError(
        module.name,
        `Full file read fallback failed (${module.path}: ${errMsg})`,
      );
      return false;
    }
  }
}
