import type { StorageConfig, NextStateError } from '../types/types';
import { createStorage, StorageAdapter } from './adapters';

interface StorageOperation {
  type: 'set' | 'remove' | 'clear';
  key?: string;
  value?: unknown;
  timestamp: number;
}

export class StorageManager<T> {
  private adapter: StorageAdapter<T>;
  private pendingOperations: StorageOperation[] = [];
  private batchTimeout: NodeJS.Timeout | null = null;
  private retryCount = 0;
  private maxRetries = 3;
  private batchDelay = 100; // ms
  private retryDelay = 1000; // ms

  constructor(
    private config: StorageConfig<T>,
    type: 'localStorage' | 'indexedDB' | 'memory' = 'localStorage'
  ) {
    this.adapter = createStorage(config, type);
  }

  async get(key: string): Promise<T | null> {
    try {
      // Apply any pending operations before reading
      await this.flushPendingOperations();
      return await this.adapter.get(key);
    } catch (error) {
      return this.handleError('get', error, key);
    }
  }

  set(key: string, value: T): void {
    this.queueOperation({
      type: 'set',
      key,
      value,
      timestamp: Date.now(),
    });
  }

  remove(key: string): void {
    this.queueOperation({
      type: 'remove',
      key,
      timestamp: Date.now(),
    });
  }

  clear(): void {
    this.queueOperation({
      type: 'clear',
      timestamp: Date.now(),
    });
  }

  private queueOperation(operation: StorageOperation): void {
    this.pendingOperations.push(operation);
    this.scheduleBatch();
  }

  private scheduleBatch(): void {
    if (this.batchTimeout) {
      clearTimeout(this.batchTimeout);
    }

    this.batchTimeout = setTimeout(
      () => this.flushPendingOperations(),
      this.batchDelay
    );
  }

  private async flushPendingOperations(): Promise<void> {
    if (!this.pendingOperations.length) return;

    const operations = [...this.pendingOperations];
    this.pendingOperations = [];

    try {
      // Group operations by type and key
      const grouped = operations.reduce((acc, op) => {
        const key = `${op.type}-${op.key || 'clear'}`;
        // Only keep the latest operation for each key
        acc.set(key, op);
        return acc;
      }, new Map<string, StorageOperation>());

      // Execute operations in order: clear -> remove -> set
      for (const op of Array.from(grouped.values()).sort((a, b) => {
        const priority = { clear: 0, remove: 1, set: 2 };
        return priority[a.type] - priority[b.type];
      })) {
        switch (op.type) {
          case 'set':
            if (op.key) {
              await this.adapter.set(op.key, op.value as T);
            }
            break;
          case 'remove':
            if (op.key) {
              await this.adapter.remove(op.key);
            }
            break;
          case 'clear':
            await this.adapter.clear();
            break;
        }
      }

      this.retryCount = 0;
    } catch (error) {
      // On error, requeue operations and retry
      this.handleError('batch', error);
      if (this.retryCount < this.maxRetries) {
        this.retryCount++;
        this.pendingOperations = [...operations, ...this.pendingOperations];
        setTimeout(
          () => this.flushPendingOperations(),
          this.retryDelay * this.retryCount
        );
      } else {
        // After max retries, clear pending operations to prevent infinite loop
        this.pendingOperations = [];
        this.retryCount = 0;
        throw {
          code: 'STORAGE_ERROR',
          message: 'Max retry attempts reached for storage operations',
          details: { error, operations },
        } as NextStateError;
      }
    }
  }

  private handleError(
    operation: string,
    error: unknown,
    key?: string
  ): never | null {
    if (operation === 'get') {
      console.error(`Storage error during ${operation}:`, error);
      return null;
    }

    throw {
      code: 'STORAGE_ERROR',
      message: `Failed to ${operation} data in storage`,
      details: { error, key },
    } as NextStateError;
  }

  // Utility methods
  async getSize(): Promise<number> {
    try {
      const key = this.config.key as string;
      const data = await this.adapter.get(key);
      if (!data) return 0;
      
      const serialized = JSON.stringify(data);
      return new Blob([serialized]).size;
    } catch {
      return 0;
    }
  }

  async compact(): Promise<void> {
    try {
      const key = this.config.key as string;
      const data = await this.adapter.get(key);
      if (!data) return;

      // Remove undefined and null values from objects
      const compacted = JSON.parse(
        JSON.stringify(data, (_, value) => 
          value === null || value === undefined ? undefined : value
        )
      );

      await this.adapter.set(key, compacted);
    } catch (error) {
      this.handleError('compact', error);
    }
  }
} 