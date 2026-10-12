import { Constants } from '../config/constants.js';
import { Logger } from '../utils/logger.js';
import { ModuleDumper } from '../core/moduleDumper.js';
import { readCString } from '../utils/memoryUtils.js';

/**
 * Interface for the Interceptor context data.
 */
interface InterceptorContext {
  libpath: string | null;
}

/**
 * Class responsible for hooking library loading functions.
 */
export class LibraryLoaderHook {
  private readonly logger: Logger;
  private readonly moduleDumper: ModuleDumper;
  private readonly hookedFunctions: Set<string>;

  /**
   * Creates a new LibraryLoaderHook instance.
   *
   * @param {Logger} logger - Logger instance for output.
   * @param {ModuleDumper} moduleDumper - ModuleDumper for dumping loaded modules.
   */
  constructor(logger: Logger, moduleDumper: ModuleDumper) {
    this.logger = logger;
    this.moduleDumper = moduleDumper;
    this.hookedFunctions = new Set<string>();
  }

  /**
   * Gets all hooked function names.
   *
   * @returns {Set<string>} Set of hooked function names.
   */
  public getHookedFunctions(): Set<string> {
    return new Set(this.hookedFunctions);
  }

  /**
   * Sets up an Interceptor hook on a library loading function.
   *
   * @param {string} functionName - The name of the function to hook (e.g., "dlopen").
   * @returns {boolean} True if hook was successfully placed, false otherwise.
   */
  public hookLibraryLoader(functionName: string): boolean {
    // Check if already hooked
    if (this.hookedFunctions.has(functionName)) {
      this.logger.log(`${functionName} already hooked, skipping.`);
      return true;
    }

    // Find the function's address by scanning all loaded modules
    let exportPtr: NativePointer | null = null;
    try {
      for (const mod of Process.enumerateModules()) {
        const ptr = mod.findExportByName(functionName);
        if (ptr) {
          exportPtr = ptr;
          break;
        }
      }
    } catch (error) {
      this.logger.error(
        `Export lookup failed for ${functionName}`,
        error instanceof Error ? error : new Error(String(error)),
      );
      return false;
    }

    if (!exportPtr) {
      this.logger.warn(`${functionName} export not found. Hook not set.`);
      return false;
    }

    this.logger.log(`Found ${functionName} at ${exportPtr}. Attaching interceptor...`);
    try {
      const dumper = this.moduleDumper;
      const log = this.logger;

      Interceptor.attach(exportPtr, {
        onEnter(args) {
          (this as unknown as InterceptorContext).libpath = null;
          try {
            if (args[0] && !args[0].isNull()) {
              (this as unknown as InterceptorContext).libpath = readCString(args[0]);
            }
          } catch (error) {
            log.warn(
              `Failed to read library path in ${functionName}.onEnter: ${
                error instanceof Error ? error.message : String(error)
              }`,
            );
          }
        },
        onLeave(retval) {
          const path = (this as unknown as InterceptorContext).libpath;

          if (path && path.includes('.so') && retval && !retval.isNull()) {
            setTimeout(() => {
              try {
                const module =
                  Process.findModuleByName(path) || Process.findModuleByAddress(retval);
                if (module) {
                  dumper.dumpModule(module);
                } else {
                  log.warn(
                    `${functionName} finished for ${path}, but couldn't find module info (handle: ${retval}).`,
                  );
                }
              } catch (error) {
                log.error(
                  `Error in ${functionName}.onLeave callback for ${path}`,
                  error instanceof Error ? error : new Error(String(error)),
                );
              }
            }, Constants.LOADER_HOOK_DELAY_MS);
          }
        },
      });

      this.hookedFunctions.add(functionName);
      this.logger.log(`Hooked ${functionName} successfully.`);
      return true;
    } catch (error) {
      this.logger.error(
        `Failed to attach interceptor to ${functionName} at ${exportPtr}`,
        error instanceof Error ? error : new Error(String(error)),
      );
      return false;
    }
  }
}
