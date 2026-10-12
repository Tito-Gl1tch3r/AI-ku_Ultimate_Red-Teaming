import { type StateConfig } from '../types/types';

export interface ServerStateConfig<T> extends StateConfig<T> {
  cache?: {
    ttl?: number;
    staleWhileRevalidate?: boolean;
  };
  revalidate?: {
    interval?: number;
    onFocus?: boolean;
    onReconnect?: boolean;
  };
}

export interface ServerState<T> {
  revalidate: () => Promise<void>;
  mutate: (data: Partial<T>) => Promise<void>;
  invalidate: () => Promise<void>;
}

export const createServerState = <T extends object>(
  config: ServerStateConfig<T>
): ServerState<T> => {
  // Implementation will be in separate files
  throw new Error('Not implemented');
};

// Export server-specific middleware
export { createServerMiddleware } from '../middleware/middleware-registry';
export { createStorage } from '../storage/storage';
export { createServerCache } from './cache';

// Export server utilities
export { withServerState } from './with-server-state';
export { createServerAction } from './actions';
export { createServerSelector } from './selectors';
