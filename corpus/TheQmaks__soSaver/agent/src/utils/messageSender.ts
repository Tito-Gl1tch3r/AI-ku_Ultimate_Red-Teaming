/**
 * Types of messages that can be sent to the host.
 */
export enum MessageType {
  MODULE_INFO = 'module_info',
  MODULE_CHUNK = 'module_chunk',
  MODULE_COMPLETE = 'module_complete',
  MODULE_ERROR = 'module_error',
  ERROR = 'error',
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
export type Message =
  | ModuleInfoMessage
  | ModuleChunkMessage
  | ModuleCompleteMessage
  | ModuleErrorMessage
  | ErrorMessage;

/**
 * Utility class for sending messages to the host.
 */
export class MessageSender {
  /**
   * Sends module information to the host.
   *
   * @param {string} name - Module name.
   * @param {*} base - Module base address.
   * @param {number} size - Module size in bytes.
   * @param {string|null} path - Module file path (if available).
   * @returns {void}
   */
  public sendModuleInfo(
    name: string,
    base: NativePointer,
    size: number,
    path: string | null,
  ): void {
    send({
      type: MessageType.MODULE_INFO,
      module: name,
      base: base.toString(),
      size: size,
      path: path,
    });
  }

  /**
   * Sends a module data chunk to the host.
   *
   * @param {string} name - Module name.
   * @param {number} offset - Offset of the chunk in the module.
   * @param {ArrayBuffer} data - Chunk data as ArrayBuffer.
   * @returns {void}
   */
  public sendModuleChunk(name: string, offset: number, data: ArrayBuffer): void {
    send(
      {
        type: MessageType.MODULE_CHUNK,
        module: name,
        offset: offset,
        chunk_size: data.byteLength,
      },
      data,
    );
  }

  /**
   * Sends a message indicating module dump is complete.
   *
   * @param {string} name - Module name.
   * @returns {void}
   */
  public sendModuleComplete(name: string): void {
    send({
      type: MessageType.MODULE_COMPLETE,
      module: name,
    });
  }

  /**
   * Sends a module-specific error message to the host.
   *
   * @param {string} name - Module name.
   * @param {string} error - Error message.
   * @returns {void}
   */
  public sendModuleError(name: string, error: string): void {
    send({
      type: MessageType.MODULE_ERROR,
      module: name,
      error: error,
    });
  }

  /**
   * Sends a generic error message to the host.
   *
   * @param {string} message - Error message.
   * @returns {void}
   */
  public sendError(message: string): void {
    send({
      type: MessageType.ERROR,
      message: message,
    });
  }
}
