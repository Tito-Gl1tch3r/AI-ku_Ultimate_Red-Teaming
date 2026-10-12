import { ReactNode } from 'react';

// Core state types
export interface StateConfig<T extends object> {
  initialState: T;
  options?: StateOptions;
}

export interface StateOptions {
  devTools?: boolean;
  storage?: StorageOptions;
}

export interface StorageOptions {
  key: string;
  version: string;
  serialize?: (data: unknown) => string;
  deserialize?: (data: string) => { version: string; data: unknown };
  migrations?: Record<string, (data: unknown) => unknown>;
}

// Action types
export type Action<T> = (state: T) => Partial<T>;
export type AsyncAction<T> = (state: T) => Promise<Partial<T>>;
export type StateUpdate<T> = Partial<T>;

// Selector types
export type Selector<T, R> = (state: T) => R;

// Middleware types
export type Middleware<T = any> = (
  state: T,
  nextState: Partial<T>
) => Partial<T> | Promise<Partial<T>>;

// Provider props
export interface ProviderProps {
  children: ReactNode;
  initialState?: any;
}

// Error types
export interface INextStateError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

// State snapshot for devtools
export interface StateSnapshot<T> {
  state: T;
  timestamp: number;
}

// Storage interface
export interface Storage {
  getItem: (key: string) => Promise<string | null>;
  setItem: (key: string, value: string) => Promise<void>;
  removeItem: (key: string) => Promise<void>;
}

// Dev tools types
export type DeepReadonly<T> = {
  readonly [P in keyof T]: T[P] extends object ? DeepReadonly<T[P]> : T[P];
};

export interface PerformanceMetrics {
  updateTime: number;
  renderTime: number;
  memoryUsage: number;
}

// Utility types
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

export type EqualityFn<T> = (a: T, b: T) => boolean;

// Server state types
export interface ServerState<T> {
  get(): Promise<T>;
  set(update: DeepPartial<T>): Promise<void>;
  subscribe(listener: () => void): () => void;
  revalidate(tags?: string[]): Promise<void>;
}

// Performance monitoring types
export interface PerformanceMonitor {
  now(): number;
  track(event: string, duration: number): void;
  getMetrics(): {
    updates: number;
    avgUpdateTime: number;
    lastUpdateTime: number;
  };
}

// Listener set type
export interface ListenerSet<T> {
  add(listener: (state: T) => void): void;
  delete(listener: (state: T) => void): void;
  notify(state: T, performance: PerformanceMonitor): void;
}

export type NextStateConfig<T extends object> = StateConfig<T>;
export type NextStateHook<T extends object> = (config: NextStateConfig<T>) => T;

export type NextStateError = INextStateError;
export type EnhancedMiddleware<T> = Middleware<T>;
export type StorageConfig<T> = StorageOptions;
export type StorageAdapter<T> = Storage;
export type MigrationFn<T> = (data: T) => T;

export type NextStateStorageConfig<T> = StorageConfig<T>;
export type NextStateStorageAdapter<T> = StorageAdapter<T>;
export type NextStateMigrationFn<T> = MigrationFn<T>;
