/**
 * Logger utility class for handling console output with consistent formatting.
 */
export class Logger {
  private readonly prefix: string;

  /**
   * Creates a new logger instance.
   *
   * @param {string} prefix - Optional prefix to add to all log messages.
   */
  constructor(prefix = '[Frida]') {
    this.prefix = prefix;
  }

  /**
   * Logs an informational message to the console.
   *
   * @param {string} message - The message to log.
   * @returns {void}
   */
  public log(message: string): void {
    console.log(`${this.prefix} ${message}`);
  }

  /**
   * Logs a warning message to the console.
   *
   * @param {string} message - The warning message to log.
   * @returns {void}
   */
  public warn(message: string): void {
    console.warn(`${this.prefix} ${message}`);
  }

  /**
   * Logs an error message to the console.
   *
   * @param {string} message - The error message to log.
   * @param {Error} [error] - Optional Error object to include in the log.
   * @returns {void}
   */
  public error(message: string, error?: Error): void {
    if (error) {
      console.error(`${this.prefix} ${message}: ${error.message}`);
      if (error.stack) {
        console.error(`${this.prefix} Stack: ${error.stack}`);
      }
    } else {
      console.error(`${this.prefix} ${message}`);
    }
  }
}
