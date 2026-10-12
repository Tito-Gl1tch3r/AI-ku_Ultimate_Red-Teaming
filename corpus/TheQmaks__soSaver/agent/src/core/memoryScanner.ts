import { Logger } from '../utils/logger.js';
import { MessageSender } from '../utils/messageSender.js';
import { ModuleDumper } from './moduleDumper.js';
import { readMemoryBytes } from '../utils/memoryUtils.js';

/**
 * Class responsible for scanning memory to find ELF headers and discovering modules.
 */
export class MemoryScanner {
  private readonly logger: Logger;
  private readonly messageSender: MessageSender;
  private readonly moduleDumper: ModuleDumper;

  /**
   * Creates a new MemoryScanner instance.
   *
   * @param {Logger} logger - Logger instance for output.
   * @param {MessageSender} messageSender - MessageSender for sending data to host.
   * @param {ModuleDumper} moduleDumper - ModuleDumper for dumping discovered modules.
   */
  constructor(logger: Logger, messageSender: MessageSender, moduleDumper: ModuleDumper) {
    this.logger = logger;
    this.messageSender = messageSender;
    this.moduleDumper = moduleDumper;
  }

  /**
   * Scans memory ranges with 'r-x' protection for ELF headers.
   * If an ELF header is found, identifies the module and calls dumpModule if not already dumped.
   *
   * @returns {number} Number of new modules found and processed.
   */
  public scanMemoryForELF(): number {
    try {
      const ranges = Process.enumerateRanges({ protection: 'r-x', coalesce: true });
      let foundCount = 0;

      ranges.forEach((range) => {
        try {
          // Basic checks for valid range and minimum size
          if (range.base.isNull() || range.size < 4) return;

          // Read only the first 4 bytes for ELF magic number check
          const header = readMemoryBytes(range.base, 4);
          if (!header) return; // Read failed for this range

          const headerBytes = new Uint8Array(header);
          // Check for ELF magic: 0x7F 'E' 'L' 'F'
          if (
            headerBytes[0] === 0x7f &&
            headerBytes[1] === 0x45 &&
            headerBytes[2] === 0x4c &&
            headerBytes[3] === 0x46
          ) {
            // Found ELF header, try to resolve module
            const mod = Process.findModuleByAddress(range.base);
            // Check if it's a valid module, has a .so name, and hasn't been processed
            if (mod && mod.name && mod.name.includes('.so')) {
              if (!this.moduleDumper.isModuleDumped(mod.name)) {
                this.logger.log(
                  `Found potential module ${mod.name} via memory scan at ${range.base}`,
                );
                if (this.moduleDumper.dumpModule(mod)) {
                  foundCount++;
                }
              }
            }
          }
        } catch (error) {
          // Ignore errors scanning individual ranges (e.g., permission denied)
        }
      }); // End forEach range

      if (foundCount > 0) {
        this.logger.log(`Memory scan initiated dump for ${foundCount} new modules.`);
      }
      return foundCount;
    } catch (scanError) {
      // Error enumerating ranges itself
      this.logger.error(
        `Error during memory scan (enumerateRangesSync)`,
        scanError instanceof Error ? scanError : new Error(String(scanError)),
      );
      this.messageSender.sendError(
        `Memory scan failed: ${scanError instanceof Error ? scanError.message : String(scanError)}`,
      );
      return 0;
    }
  }

  /**
   * Scans for newly loaded modules that haven't been dumped yet.
   *
   * @returns {number} Number of new modules found and processed.
   */
  public scanForNewModules(): number {
    let foundCount = 0;
    try {
      // Check modules known to Frida's Process API
      Process.enumerateModules().forEach((module) => {
        // If a .so module is found that hasn't been processed, dump it
        if (module.name.includes('.so') && !this.moduleDumper.isModuleDumped(module.name)) {
          this.logger.log(`Found new module via periodic enumeration: ${module.name}`);
          if (this.moduleDumper.dumpModule(module)) {
            foundCount++;
          }
        }
      });
    } catch (error) {
      this.logger.error(
        `Error during module enumeration`,
        error instanceof Error ? error : new Error(String(error)),
      );
    }

    return foundCount;
  }
}
