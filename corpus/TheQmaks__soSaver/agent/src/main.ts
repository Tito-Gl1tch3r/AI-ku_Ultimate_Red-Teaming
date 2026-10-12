import { Constants } from './config/constants.js';
import { MemoryScanner } from './core/memoryScanner.js';
import { ModuleDumper } from './core/moduleDumper.js';
import { LibraryLoaderHook } from './hooks/libraryLoaderHook.js';
import { Logger } from './utils/logger.js';
import { MessageSender } from './utils/messageSender.js';

/**
 * Main agent class that orchestrates all components.
 */
class SoSaverAgent {
  private readonly logger: Logger;
  private readonly messageSender: MessageSender;
  private readonly moduleDumper: ModuleDumper;
  private readonly memoryScanner: MemoryScanner;
  private readonly libraryLoaderHook: LibraryLoaderHook;

  /**
   * Creates a new SoSaverAgent instance.
   */
  constructor() {
    this.logger = new Logger('[Frida]');
    this.messageSender = new MessageSender();
    this.moduleDumper = new ModuleDumper(this.logger, this.messageSender);
    this.memoryScanner = new MemoryScanner(this.logger, this.messageSender, this.moduleDumper);
    this.libraryLoaderHook = new LibraryLoaderHook(this.logger, this.moduleDumper);

    this.logger.log('soSaver agent initialized.');
  }

  /**
   * Performs initial dump of all currently loaded modules.
   */
  private performInitialModuleDump(): void {
    try {
      this.logger.log('Performing initial module enumeration...');
      Process.enumerateModules().forEach((module) => {
        if (module.name.includes('.so')) {
          this.moduleDumper.dumpModule(module);
        }
      });
      this.logger.log('Initial module enumeration complete.');
    } catch (error) {
      this.logger.error(
        'Error during initial module enumeration',
        error instanceof Error ? error : new Error(String(error)),
      );
      this.messageSender.sendError(
        `Initial enumeration failed: ${error instanceof Error ? error.message : String(error)}`,
      );
    }
  }

  /**
   * Sets up hooks on library loading functions.
   */
  private setupLibraryHooks(): void {
    this.logger.log('Setting up library load hooks...');

    this.libraryLoaderHook.hookLibraryLoader('dlopen');
    this.libraryLoaderHook.hookLibraryLoader('android_dlopen_ext');

    this.logger.log('Library load hooks setup complete.');
  }

  /**
   * Starts periodic scanning for new modules and ELF headers.
   */
  private startPeriodicScanning(): void {
    this.logger.log(`Starting periodic scan every ${Constants.SCAN_INTERVAL_MS}ms...`);

    setInterval(() => {
      try {
        this.memoryScanner.scanForNewModules();
        this.memoryScanner.scanMemoryForELF();
      } catch (error) {
        this.logger.error(
          'Error during periodic scan',
          error instanceof Error ? error : new Error(String(error)),
        );
        this.messageSender.sendError(
          `Periodic scan failed: ${error instanceof Error ? error.message : String(error)}`,
        );
      }
    }, Constants.SCAN_INTERVAL_MS);
  }

  /**
   * Starts the soSaver agent by initializing all components and scanning for modules.
   */
  public start(): void {
    this.logger.log('Starting soSaver agent...');

    this.performInitialModuleDump();
    this.setupLibraryHooks();
    this.startPeriodicScanning();

    this.logger.log('soSaver agent initialization complete. Waiting for events...');
  }
}

// Create and start the application when the script loads
try {
  const agent = new SoSaverAgent();
  agent.start();
} catch (error) {
  const msg = error instanceof Error ? error.message : String(error);
  const stack = error instanceof Error ? error.stack : '';
  console.error(`[Frida] Fatal error during soSaver agent initialization: ${msg}`);
  if (stack) {
    console.error(`[Frida] Stack trace: ${stack}`);
  }
}
