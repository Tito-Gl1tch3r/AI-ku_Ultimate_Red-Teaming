import type { PerformanceMetrics, DebugLogger } from './types';

export const createPerformanceMonitor = () => {
  const monitor = {
    updates: 0,
    listeners: 0,
    lastUpdateTime: 0,
    updateTimes: [] as number[],
    
    track(type: 'update' | 'notify', duration?: number) {
      this[type === 'update' ? 'updates' : 'listeners']++;
      if (duration) {
        this.updateTimes.push(duration);
        this.lastUpdateTime = duration;
      }
    },
    
    getMetrics(): PerformanceMetrics {
      const avgUpdateTime = this.updateTimes.length 
        ? this.updateTimes.reduce((a, b) => a + b, 0) / this.updateTimes.length 
        : 0;
      return {
        updates: this.updates,
        listeners: this.listeners,
        avgUpdateTime,
        lastUpdateTime: this.lastUpdateTime,
      };
    },
  };

  return monitor;
};

export const createDebugLogger = (enabled: boolean): DebugLogger => ({
  log(action: string, data: unknown) {
    if (enabled && process.env.NODE_ENV === 'development') {
      console.log(`[NextState] ${action}:`, data);
    }
  },
  error(action: string, error: unknown) {
    if (enabled) {
      console.error(`[NextState] Error in ${action}:`, error);
    }
  }
});

export function deepMerge<T>(target: T, source: Partial<T>): T {
  if (!source || typeof source !== 'object') return source as T;
  if (!target || typeof target !== 'object') return target;

  const result = { ...target };
  for (const key in source) {
    if (Object.prototype.hasOwnProperty.call(source, key)) {
      const sourceValue = source[key];
      const targetValue = target[key];

      result[key] = (sourceValue && typeof sourceValue === 'object' && targetValue)
        ? deepMerge(targetValue, sourceValue)
        : sourceValue as any;
    }
  }
  return result;
}

export class ListenerSet<T> {
  private listeners = new Set<WeakRef<(state: T) => void>>();
  private cleanupInterval: ReturnType<typeof setInterval>;
  private debugLogger: DebugLogger;

  constructor(debugEnabled: boolean) {
    this.debugLogger = createDebugLogger(debugEnabled);
    this.cleanupInterval = setInterval(() => this.cleanup(), 60000);
  }

  add(listener: (state: T) => void): void {
    this.listeners.add(new WeakRef(listener));
    this.debugLogger.log('Listener added', { totalListeners: this.listeners.size });
  }

  delete(listener: (state: T) => void): void {
    for (const ref of this.listeners) {
      if (ref.deref() === listener) {
        this.listeners.delete(ref);
        this.debugLogger.log('Listener removed', { totalListeners: this.listeners.size });
        break;
      }
    }
  }

  notify(state: T, performance: ReturnType<typeof createPerformanceMonitor>): void {
    const startTime = performance.now();
    let notifiedCount = 0;

    for (const ref of this.listeners) {
      const listener = ref.deref();
      if (listener) {
        try {
          listener(state);
          notifiedCount++;
        } catch (error) {
          this.debugLogger.error('listener notification', error);
        }
      }
    }

    const duration = performance.now() - startTime;
    performance.track('notify', duration);
    this.debugLogger.log('Listeners notified', { notifiedCount, duration });
  }

  private cleanup(): void {
    const initialSize = this.listeners.size;
    for (const ref of this.listeners) {
      if (!ref.deref()) {
        this.listeners.delete(ref);
      }
    }
    
    const removedCount = initialSize - this.listeners.size;
    if (removedCount > 0) {
      this.debugLogger.log('Listener cleanup', { removedCount, remainingListeners: this.listeners.size });
    }
  }

  dispose(): void {
    clearInterval(this.cleanupInterval);
    this.listeners.clear();
    this.debugLogger.log('ListenerSet disposed', { finalListenerCount: 0 });
  }
} 