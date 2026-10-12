import { createContext } from 'react';
import type { DeepPartial } from '../types/types';

export interface NextStateStore<T extends object> {
  getState: () => T;
  setState: (update: DeepPartial<T>) => void;
  subscribe: (listener: (state: T) => void) => () => void;
  getInitialState: () => T;
  syncWithServer: (update: DeepPartial<T>) => Promise<void>;
  loadPersistedState: (key: string) => Promise<void>;
  persistState: (key: string, state: T) => Promise<void>;
  subscribeWithKey: (key: string, listener: (state: T) => void) => () => void;
}

export const StateContext = createContext<NextStateStore<any> | null>(null);

// Type guard for checking if store exists
export function assertStore<T extends object>(
  store: NextStateStore<T> | null,
  hookName: string
): asserts store is NextStateStore<T> {
  if (!store) {
    throw new Error(`${hookName} must be used within NextStateProvider`);
  }
}

// Helper type for wrapped components
export type WithNextState<P = {}> = P & {
  store: NextStateStore<any>;
};

// Helper type for async state
export type AsyncState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; error: Error };

// Helper type for optimistic updates
export type OptimisticUpdate<T> = {
  update: DeepPartial<T>;
  timestamp: number;
  status: 'pending' | 'success' | 'error';
};

// Helper type for state history
export type StateHistoryEntry<T> = {
  state: T;
  timestamp: number;
  action?: string;
};

// Helper type for state persistence
export type PersistenceConfig = {
  key: string;
  throttle?: number;
  serialize?: (data: any) => string;
  deserialize?: (data: string) => any;
};

// Helper type for state subscriptions
export type Subscription<T> = {
  id: string;
  listener: (state: T) => void;
  selector?: (state: T) => any;
  equalityFn?: (a: any, b: any) => boolean;
};

// Helper type for state updates
export type StateUpdate<T> = {
  type: 'set' | 'merge' | 'reset';
  payload: DeepPartial<T>;
  meta?: Record<string, unknown>;
};

// Helper type for state actions
export type StateAction<T, P = void> = {
  type: string;
  execute: (state: T, payload: P) => DeepPartial<T> | Promise<DeepPartial<T>>;
  onSuccess?: (state: T, payload: P, result: DeepPartial<T>) => void;
  onError?: (state: T, payload: P, error: Error) => void;
};

// Helper type for state middleware
export type StateMiddleware<T> = {
  id: string;
  before?: (update: StateUpdate<T>) => StateUpdate<T> | null;
  after?: (state: T, update: StateUpdate<T>) => void;
  onError?: (error: Error, update: StateUpdate<T>) => void;
};

// Helper type for state selectors
export type StateSelector<T, R> = {
  select: (state: T) => R;
  dependencies?: Array<(state: T) => any>;
  equalityFn?: (prev: R, next: R) => boolean;
}; 