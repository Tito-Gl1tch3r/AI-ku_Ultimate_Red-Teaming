📦
2208 /src/main.js
437 /src/config/constants.d.ts
88 /src/config/constants.js
1262 /src/core/memoryScanner.d.ts
1346 /src/core/memoryScanner.js
2157 /src/core/moduleDumper.d.ts
2866 /src/core/moduleDumper.js
1066 /src/hooks/libraryLoaderHook.d.ts
1594 /src/hooks/libraryLoaderHook.js
11 /src/main.d.ts
966 /src/utils/logger.d.ts
308 /src/utils/logger.js
745 /src/utils/memoryUtils.d.ts
235 /src/utils/memoryUtils.js
2965 /src/utils/messageSender.d.ts
645 /src/utils/messageSender.js
✄
import{Constants as r}from"./config/constants.js";import{MemoryScanner as e}from"./core/memoryScanner.js";import{ModuleDumper as o}from"./core/moduleDumper.js";import{LibraryLoaderHook as i}from"./hooks/libraryLoaderHook.js";import{Logger as t}from"./utils/logger.js";import{MessageSender as s}from"./utils/messageSender.js";class n{constructor(){this.logger=new t("[Frida]"),this.messageSender=new s,this.moduleDumper=new o(this.logger,this.messageSender),this.memoryScanner=new e(this.logger,this.messageSender,this.moduleDumper),this.libraryLoaderHook=new i(this.logger,this.moduleDumper),this.logger.log("soSaver agent initialized.")}performInitialModuleDump(){try{this.logger.log("Performing initial module enumeration..."),Process.enumerateModules().forEach((r=>{r.name.includes(".so")&&this.moduleDumper.dumpModule(r)})),this.logger.log("Initial module enumeration complete.")}catch(r){this.logger.error("Error during initial module enumeration",r instanceof Error?r:new Error(String(r))),this.messageSender.sendError(`Initial enumeration failed: ${r instanceof Error?r.message:String(r)}`)}}setupLibraryHooks(){this.logger.log("Setting up library load hooks..."),this.libraryLoaderHook.hookLibraryLoader("dlopen"),this.libraryLoaderHook.hookLibraryLoader("android_dlopen_ext"),this.logger.log("Library load hooks setup complete.")}startPeriodicScanning(){this.logger.log(`Starting periodic scan every ${r.SCAN_INTERVAL_MS}ms...`),setInterval((()=>{try{this.memoryScanner.scanForNewModules(),this.memoryScanner.scanMemoryForELF()}catch(r){this.logger.error("Error during periodic scan",r instanceof Error?r:new Error(String(r))),this.messageSender.sendError(`Periodic scan failed: ${r instanceof Error?r.message:String(r)}`)}}),r.SCAN_INTERVAL_MS)}start(){this.logger.log("Starting soSaver agent..."),this.performInitialModuleDump(),this.setupLibraryHooks(),this.startPeriodicScanning(),this.logger.log("soSaver agent initialization complete. Waiting for events...")}}try{(new n).start()}catch(r){const e=r instanceof Error?r.message:String(r),o=r instanceof Error?r.stack:"";console.error(`[Frida] Fatal error during soSaver agent initialization: ${e}`),o&&console.error(`[Frida] Stack trace: ${o}`)}
✄
/**
 * Configuration constants for the SO Saver Frida script.
 */
export declare const Constants: {
    /**
     * Size of memory chunks to read and send (in bytes).
     */
    CHUNK_SIZE: number;
    /**
     * Interval for periodic memory scans (in milliseconds).
     */
    SCAN_INTERVAL_MS: number;
    /**
     * Delay after dlopen returns before finding the module (in milliseconds).
     */
    LOADER_HOOK_DELAY_MS: number;
};

✄
export const Constants={CHUNK_SIZE:65536,SCAN_INTERVAL_MS:1e4,LOADER_HOOK_DELAY_MS:250};
✄
import { Logger } from '../utils/logger.js';
import { MessageSender } from '../utils/messageSender.js';
import { ModuleDumper } from './moduleDumper.js';
/**
 * Class responsible for scanning memory to find ELF headers and discovering modules.
 */
export declare class MemoryScanner {
    private readonly logger;
    private readonly messageSender;
    private readonly moduleDumper;
    /**
     * Creates a new MemoryScanner instance.
     *
     * @param {Logger} logger - Logger instance for output.
     * @param {MessageSender} messageSender - MessageSender for sending data to host.
     * @param {ModuleDumper} moduleDumper - ModuleDumper for dumping discovered modules.
     */
    constructor(logger: Logger, messageSender: MessageSender, moduleDumper: ModuleDumper);
    /**
     * Scans memory ranges with 'r-x' protection for ELF headers.
     * If an ELF header is found, identifies the module and calls dumpModule if not already dumped.
     *
     * @returns {number} Number of new modules found and processed.
     */
    scanMemoryForELF(): number;
    /**
     * Scans for newly loaded modules that haven't been dumped yet.
     *
     * @returns {number} Number of new modules found and processed.
     */
    scanForNewModules(): number;
}

✄
import{readMemoryBytes as e}from"../utils/memoryUtils.js";export class MemoryScanner{constructor(e,r,o){this.logger=e,this.messageSender=r,this.moduleDumper=o}scanMemoryForELF(){try{const r=Process.enumerateRanges({protection:"r-x",coalesce:!0});let o=0;return r.forEach((r=>{try{if(r.base.isNull()||r.size<4)return;const s=e(r.base,4);if(!s)return;const n=new Uint8Array(s);if(127===n[0]&&69===n[1]&&76===n[2]&&70===n[3]){const e=Process.findModuleByAddress(r.base);e&&e.name&&e.name.includes(".so")&&(this.moduleDumper.isModuleDumped(e.name)||(this.logger.log(`Found potential module ${e.name} via memory scan at ${r.base}`),this.moduleDumper.dumpModule(e)&&o++))}}catch(e){}})),o>0&&this.logger.log(`Memory scan initiated dump for ${o} new modules.`),o}catch(e){return this.logger.error("Error during memory scan (enumerateRangesSync)",e instanceof Error?e:new Error(String(e))),this.messageSender.sendError(`Memory scan failed: ${e instanceof Error?e.message:String(e)}`),0}}scanForNewModules(){let e=0;try{Process.enumerateModules().forEach((r=>{r.name.includes(".so")&&!this.moduleDumper.isModuleDumped(r.name)&&(this.logger.log(`Found new module via periodic enumeration: ${r.name}`),this.moduleDumper.dumpModule(r)&&e++)}))}catch(e){this.logger.error("Error during module enumeration",e instanceof Error?e:new Error(String(e)))}return e}}
✄
/// <reference types="frida-gum" />
import { Logger } from '../utils/logger.js';
import { MessageSender } from '../utils/messageSender.js';
/**
 * Class responsible for dumping module data from memory or file system.
 */
export declare class ModuleDumper {
    private readonly logger;
    private readonly messageSender;
    private readonly dumpedModules;
    /**
     * Creates a new ModuleDumper instance.
     *
     * @param {Logger} logger - Logger instance for output.
     * @param {MessageSender} messageSender - MessageSender instance for sending data to host.
     */
    constructor(logger: Logger, messageSender: MessageSender);
    /**
     * Checks if a module has already been dumped.
     *
     * @param {string} moduleName - The module name to check.
     * @returns {boolean} True if the module has been dumped, false otherwise.
     */
    isModuleDumped(moduleName: string): boolean;
    /**
     * Gets all dumped module names.
     * Note: Primarily intended for diagnostic and debugging purposes.
     * This method provides visibility into which modules have already been processed,
     * which can be useful for troubleshooting or developing extensions.
     *
     * @returns {Set<string>} Set of all dumped module names.
     */
    getDumpedModules(): Set<string>;
    /**
     * Dumps a module, first trying to read from memory. If memory read fails,
     * attempts to read the *entire* file from disk using readAllBytes() as a fallback.
     *
     * @param {object} module - The Frida Module object to dump.
     * @returns {boolean} True if the module was successfully dumped, false otherwise.
     */
    dumpModule(module: Module): boolean;
    /**
     * Internal method to dump the module data from memory or file.
     *
     * @param {object} module - The module to dump.
     * @returns {boolean} True if successful, false otherwise.
     */
    private dumpModuleData;
    /**
     * Attempts to dump a module by reading it from disk.
     *
     * @param {object} module - The module to dump from its file path.
     * @returns {boolean} True if successful, false otherwise.
     */
    private dumpFromFile;
}

✄
import{Constants as e}from"../config/constants.js";import{readMemoryBytes as r}from"../utils/memoryUtils.js";export class ModuleDumper{constructor(e,r){this.logger=e,this.messageSender=r,this.dumpedModules=new Set}isModuleDumped(e){return this.dumpedModules.has(e)}getDumpedModules(){return new Set(this.dumpedModules)}dumpModule(e){if(!e||!e.name||!e.base||"number"!=typeof e.size)return this.logger.error(`Invalid module data received: ${JSON.stringify(e)}`),!1;if(this.dumpedModules.has(e.name))return!0;this.logger.log(`Attempting to dump ${e.name} (Base: ${e.base}, Size: ${e.size}, Path: ${e.path||"N/A"})`),this.dumpedModules.add(e.name);try{return this.messageSender.sendModuleInfo(e.name,e.base,e.size,e.path||null),0===e.size?(this.logger.warn(`Module ${e.name} reported size 0. Skipping data dump.`),this.messageSender.sendModuleComplete(e.name),!0):this.dumpModuleData(e)}catch(r){return this.logger.error(`General error during dump of ${e.name}`,r instanceof Error?r:new Error(String(r))),this.messageSender.sendModuleError(e.name,`General dump error: ${r instanceof Error?r.message:String(r)}`),!1}}dumpModuleData(t){let s=!0;for(let n=0;n<t.size;n+=e.CHUNK_SIZE){const a=Math.min(e.CHUNK_SIZE,t.size-n);try{const e=t.base.add(n),s=r(e,a);if(!s)throw new Error("Memory read returned null");this.messageSender.sendModuleChunk(t.name,n,s)}catch(e){return this.logger.warn(`Memory read failed for ${t.name} at offset ${n}: ${e instanceof Error?e.message:String(e)}. Checking file fallback...`),s=!1,t.path&&t.path.length>0?this.dumpFromFile(t):(this.logger.error(`Memory read failed for ${t.name} at offset ${n} (${e instanceof Error?e.message:String(e)}), no file path.`),this.messageSender.sendModuleError(t.name,`Memory read failed at offset ${n}: ${e instanceof Error?e.message:String(e)}. No file path for fallback.`),!1)}}return!!s&&(this.logger.log(`Finished sending chunks for ${t.name} (via memory)`),this.messageSender.sendModuleComplete(t.name),!0)}dumpFromFile(r){this.logger.log(`Path found: ${r.path}. Attempting full file read fallback...`);try{this.logger.log(`Reading all bytes from file ${r.path}...`);const t=File.readAllBytes(r.path||"");if(!t||0===t.byteLength)throw new Error("readAllBytes() returned empty or null data.");this.logger.log(`Successfully read ${t.byteLength} bytes from file. Sending chunks from file data...`);for(let s=0;s<t.byteLength;s+=e.CHUNK_SIZE){const n=Math.min(e.CHUNK_SIZE,t.byteLength-s),a=t.slice(s,s+n);this.messageSender.sendModuleChunk(r.name,s,a)}return this.logger.log(`Finished sending chunks from file ${r.name}`),this.messageSender.sendModuleComplete(r.name),!0}catch(e){const t=e instanceof Error?e.message:String(e);return this.logger.error(`Full file read fallback failed for ${r.name}: ${t}`),this.messageSender.sendModuleError(r.name,`Full file read fallback failed (${r.path}: ${t})`),!1}}}
✄
import { Logger } from '../utils/logger.js';
import { ModuleDumper } from '../core/moduleDumper.js';
/**
 * Class responsible for hooking library loading functions.
 */
export declare class LibraryLoaderHook {
    private readonly logger;
    private readonly moduleDumper;
    private readonly hookedFunctions;
    /**
     * Creates a new LibraryLoaderHook instance.
     *
     * @param {Logger} logger - Logger instance for output.
     * @param {ModuleDumper} moduleDumper - ModuleDumper for dumping loaded modules.
     */
    constructor(logger: Logger, moduleDumper: ModuleDumper);
    /**
     * Gets all hooked function names.
     *
     * @returns {Set<string>} Set of hooked function names.
     */
    getHookedFunctions(): Set<string>;
    /**
     * Sets up an Interceptor hook on a library loading function.
     *
     * @param {string} functionName - The name of the function to hook (e.g., "dlopen").
     * @returns {boolean} True if hook was successfully placed, false otherwise.
     */
    hookLibraryLoader(functionName: string): boolean;
}

✄
import{Constants as o}from"../config/constants.js";import{readCString as r}from"../utils/memoryUtils.js";export class LibraryLoaderHook{constructor(o,r){this.logger=o,this.moduleDumper=r,this.hookedFunctions=new Set}getHookedFunctions(){return new Set(this.hookedFunctions)}hookLibraryLoader(t){if(this.hookedFunctions.has(t))return this.logger.log(`${t} already hooked, skipping.`),!0;let e=null;try{for(const o of Process.enumerateModules()){const r=o.findExportByName(t);if(r){e=r;break}}}catch(o){return this.logger.error(`Export lookup failed for ${t}`,o instanceof Error?o:new Error(String(o))),!1}if(!e)return this.logger.warn(`${t} export not found. Hook not set.`),!1;this.logger.log(`Found ${t} at ${e}. Attaching interceptor...`);try{const n=this.moduleDumper,i=this.logger;return Interceptor.attach(e,{onEnter(o){this.libpath=null;try{o[0]&&!o[0].isNull()&&(this.libpath=r(o[0]))}catch(o){i.warn(`Failed to read library path in ${t}.onEnter: ${o instanceof Error?o.message:String(o)}`)}},onLeave(r){const e=this.libpath;e&&e.includes(".so")&&r&&!r.isNull()&&setTimeout((()=>{try{const o=Process.findModuleByName(e)||Process.findModuleByAddress(r);o?n.dumpModule(o):i.warn(`${t} finished for ${e}, but couldn't find module info (handle: ${r}).`)}catch(o){i.error(`Error in ${t}.onLeave callback for ${e}`,o instanceof Error?o:new Error(String(o)))}}),o.LOADER_HOOK_DELAY_MS)}}),this.hookedFunctions.add(t),this.logger.log(`Hooked ${t} successfully.`),!0}catch(o){return this.logger.error(`Failed to attach interceptor to ${t} at ${e}`,o instanceof Error?o:new Error(String(o))),!1}}}
✄
export {};

✄
/**
 * Logger utility class for handling console output with consistent formatting.
 */
export declare class Logger {
    private readonly prefix;
    /**
     * Creates a new logger instance.
     *
     * @param {string} prefix - Optional prefix to add to all log messages.
     */
    constructor(prefix?: string);
    /**
     * Logs an informational message to the console.
     *
     * @param {string} message - The message to log.
     * @returns {void}
     */
    log(message: string): void;
    /**
     * Logs a warning message to the console.
     *
     * @param {string} message - The warning message to log.
     * @returns {void}
     */
    warn(message: string): void;
    /**
     * Logs an error message to the console.
     *
     * @param {string} message - The error message to log.
     * @param {Error} [error] - Optional Error object to include in the log.
     * @returns {void}
     */
    error(message: string, error?: Error): void;
}

✄
export class Logger{constructor(r="[Frida]"){this.prefix=r}log(r){console.log(`${this.prefix} ${r}`)}warn(r){console.warn(`${this.prefix} ${r}`)}error(r,o){o?(console.error(`${this.prefix} ${r}: ${o.message}`),o.stack&&console.error(`${this.prefix} Stack: ${o.stack}`)):console.error(`${this.prefix} ${r}`)}}
✄
/**
 * Utility functions for memory operations.
 */
/// <reference types="frida-gum" />
/**
 * Read bytes from memory at the specified address.
 *
 * @param {NativePointer} address - The memory address to read from.
 * @param {number} size - Number of bytes to read.
 * @returns {ArrayBuffer | null} ArrayBuffer containing the read data, or null on failure.
 */
export declare function readMemoryBytes(address: NativePointer, size: number): ArrayBuffer | null;
/**
 * Read a C string from memory at the specified address.
 *
 * @param {NativePointer} address - The memory address to read from.
 * @returns {string | null} The read string or null if reading failed.
 */
export declare function readCString(address: NativePointer): string | null;

✄
export function readMemoryBytes(r,e){return r.readByteArray(e)}export function readCString(r){try{return r.readCString()}catch(e){return console.error(`Failed to read C string at ${r}: ${e instanceof Error?e.message:String(e)}`),null}}
✄
/// <reference types="frida-gum" />
/**
 * Types of messages that can be sent to the host.
 */
export declare enum MessageType {
    MODULE_INFO = "module_info",
    MODULE_CHUNK = "module_chunk",
    MODULE_COMPLETE = "module_complete",
    MODULE_ERROR = "module_error",
    ERROR = "error"
}
/**
 * Base interface for all messages.
 */
export interface BaseMessage {
    type: MessageType;
}
/**
 * Interface for module information messages.
 */
export interface ModuleInfoMessage extends BaseMessage {
    type: MessageType.MODULE_INFO;
    module: string;
    base: string;
    size: number;
    path: string | null;
}
/**
 * Interface for module chunk messages.
 */
export interface ModuleChunkMessage extends BaseMessage {
    type: MessageType.MODULE_CHUNK;
    module: string;
    offset: number;
    chunk_size: number;
}
/**
 * Interface for module complete messages.
 */
export interface ModuleCompleteMessage extends BaseMessage {
    type: MessageType.MODULE_COMPLETE;
    module: string;
}
/**
 * Interface for module error messages.
 */
export interface ModuleErrorMessage extends BaseMessage {
    type: MessageType.MODULE_ERROR;
    module: string;
    error: string;
}
/**
 * Interface for generic error messages.
 */
export interface ErrorMessage extends BaseMessage {
    type: MessageType.ERROR;
    message: string;
}
/**
 * Union type for all message types.
 */
export type Message = ModuleInfoMessage | ModuleChunkMessage | ModuleCompleteMessage | ModuleErrorMessage | ErrorMessage;
/**
 * Utility class for sending messages to the host.
 */
export declare class MessageSender {
    /**
     * Sends module information to the host.
     *
     * @param {string} name - Module name.
     * @param {*} base - Module base address.
     * @param {number} size - Module size in bytes.
     * @param {string|null} path - Module file path (if available).
     * @returns {void}
     */
    sendModuleInfo(name: string, base: NativePointer, size: number, path: string | null): void;
    /**
     * Sends a module data chunk to the host.
     *
     * @param {string} name - Module name.
     * @param {number} offset - Offset of the chunk in the module.
     * @param {ArrayBuffer} data - Chunk data as ArrayBuffer.
     * @returns {void}
     */
    sendModuleChunk(name: string, offset: number, data: ArrayBuffer): void;
    /**
     * Sends a message indicating module dump is complete.
     *
     * @param {string} name - Module name.
     * @returns {void}
     */
    sendModuleComplete(name: string): void;
    /**
     * Sends a module-specific error message to the host.
     *
     * @param {string} name - Module name.
     * @param {string} error - Error message.
     * @returns {void}
     */
    sendModuleError(name: string, error: string): void;
    /**
     * Sends a generic error message to the host.
     *
     * @param {string} message - Error message.
     * @returns {void}
     */
    sendError(message: string): void;
}

✄
export var MessageType;!function(e){e.MODULE_INFO="module_info",e.MODULE_CHUNK="module_chunk",e.MODULE_COMPLETE="module_complete",e.MODULE_ERROR="module_error",e.ERROR="error"}(MessageType||(MessageType={}));export class MessageSender{sendModuleInfo(e,s,o,d){send({type:MessageType.MODULE_INFO,module:e,base:s.toString(),size:o,path:d})}sendModuleChunk(e,s,o){send({type:MessageType.MODULE_CHUNK,module:e,offset:s,chunk_size:o.byteLength},o)}sendModuleComplete(e){send({type:MessageType.MODULE_COMPLETE,module:e})}sendModuleError(e,s){send({type:MessageType.MODULE_ERROR,module:e,error:s})}sendError(e){send({type:MessageType.ERROR,message:e})}}