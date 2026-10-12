import type { PerformanceMetrics } from '../types/types';

interface UpdateMetrics {
  timestamp: number;
  duration: number;
  size: number;
  type: string;
}

interface RenderMetrics {
  componentId: string;
  timestamp: number;
  duration: number;
  reason: string;
}

interface MemoryMetrics {
  timestamp: number;
  heapSize: number;
  heapUsed: number;
}

interface NetworkMetrics {
  timestamp: number;
  payloadSize: number;
  duration: number;
  type: 'sync' | 'persist' | 'load';
}

export class PerformanceMonitor {
  private static instance: PerformanceMonitor;
  private updateMetrics: UpdateMetrics[] = [];
  private renderMetrics: RenderMetrics[] = [];
  private memoryMetrics: MemoryMetrics[] = [];
  private networkMetrics: NetworkMetrics[] = [];
  private startTime = Date.now();
  private sampleInterval = 1000; // 1 second
  private maxSamples = 100;

  private constructor() {
    if (typeof window !== 'undefined') {
      // Start memory monitoring
      this.startMemoryMonitoring();
    }
  }

  static getInstance(): PerformanceMonitor {
    if (!PerformanceMonitor.instance) {
      PerformanceMonitor.instance = new PerformanceMonitor();
    }
    return PerformanceMonitor.instance;
  }

  // Track state update performance
  trackUpdate(type: string, duration: number, size: number): void {
    this.updateMetrics.push({
      timestamp: Date.now(),
      duration,
      size,
      type,
    });

    this.maintainMetricsLimit(this.updateMetrics);
  }

  // Track component render performance
  trackRender(componentId: string, duration: number, reason: string): void {
    this.renderMetrics.push({
      componentId,
      timestamp: Date.now(),
      duration,
      reason,
    });

    this.maintainMetricsLimit(this.renderMetrics);
  }

  // Track memory usage
  private startMemoryMonitoring(): void {
    const measureMemory = () => {
      if (performance.memory) {
        this.memoryMetrics.push({
          timestamp: Date.now(),
          heapSize: performance.memory.totalJSHeapSize,
          heapUsed: performance.memory.usedJSHeapSize,
        });

        this.maintainMetricsLimit(this.memoryMetrics);
      }
    };

    setInterval(measureMemory, this.sampleInterval);
  }

  // Track network operations
  trackNetwork(type: 'sync' | 'persist' | 'load', duration: number, payloadSize: number): void {
    this.networkMetrics.push({
      timestamp: Date.now(),
      duration,
      payloadSize,
      type,
    });

    this.maintainMetricsLimit(this.networkMetrics);
  }

  // Get performance metrics
  getMetrics(): PerformanceMetrics {
    const now = Date.now();
    const recentUpdates = this.updateMetrics.filter(
      m => now - m.timestamp < 60000 // Last minute
    );

    return {
      updates: recentUpdates.length,
      avgUpdateTime: this.calculateAverage(recentUpdates, 'duration'),
      lastUpdateTime: recentUpdates[recentUpdates.length - 1]?.duration || 0,
      memory: this.getMemoryMetrics(),
      network: this.getNetworkMetrics(),
      renders: this.getRenderMetrics(),
    };
  }

  // Get detailed memory metrics
  private getMemoryMetrics() {
    const recent = this.memoryMetrics[this.memoryMetrics.length - 1];
    if (!recent) return null;

    return {
      heapSize: recent.heapSize,
      heapUsed: recent.heapUsed,
      heapUtilization: recent.heapUsed / recent.heapSize,
    };
  }

  // Get detailed network metrics
  private getNetworkMetrics() {
    const recent = this.networkMetrics.slice(-10);
    return {
      totalPayloadSize: this.sum(recent, 'payloadSize'),
      avgDuration: this.calculateAverage(recent, 'duration'),
      operationCount: recent.length,
    };
  }

  // Get detailed render metrics
  private getRenderMetrics() {
    const recent = this.renderMetrics.slice(-50);
    const byComponent = this.groupBy(recent, 'componentId');

    return Object.entries(byComponent).map(([componentId, metrics]) => ({
      componentId,
      renderCount: metrics.length,
      avgDuration: this.calculateAverage(metrics, 'duration'),
      reasons: this.groupBy(metrics, 'reason'),
    }));
  }

  // Calculate bundle size
  async calculateBundleSize(): Promise<number> {
    if (typeof window === 'undefined') return 0;

    const resources = performance.getEntriesByType('resource');
    const jsResources = resources.filter(r => r.name.endsWith('.js'));
    
    let totalSize = 0;
    for (const resource of jsResources) {
      try {
        const response = await fetch(resource.name);
        const blob = await response.blob();
        totalSize += blob.size;
      } catch (error) {
        console.error('Failed to measure bundle size:', error);
      }
    }

    return totalSize;
  }

  // Utility functions
  private maintainMetricsLimit<T>(metrics: T[]): void {
    if (metrics.length > this.maxSamples) {
      metrics.splice(0, metrics.length - this.maxSamples);
    }
  }

  private calculateAverage<T>(items: T[], key: keyof T): number {
    if (!items.length) return 0;
    return this.sum(items, key) / items.length;
  }

  private sum<T>(items: T[], key: keyof T): number {
    return items.reduce((sum, item) => sum + (item[key] as number), 0);
  }

  private groupBy<T>(items: T[], key: keyof T): Record<string, T[]> {
    return items.reduce((groups, item) => {
      const value = String(item[key]);
      groups[value] = groups[value] || [];
      groups[value].push(item);
      return groups;
    }, {} as Record<string, T[]>);
  }

  // Reset metrics
  reset(): void {
    this.updateMetrics = [];
    this.renderMetrics = [];
    this.memoryMetrics = [];
    this.networkMetrics = [];
    this.startTime = Date.now();
  }
}

// Performance measurement decorator
export function measurePerformance() {
  return function (
    target: any,
    propertyKey: string,
    descriptor: PropertyDescriptor
  ) {
    const originalMethod = descriptor.value;

    descriptor.value = function (...args: any[]) {
      const start = performance.now();
      const result = originalMethod.apply(this, args);

      if (result instanceof Promise) {
        return result.finally(() => {
          const duration = performance.now() - start;
          PerformanceMonitor.getInstance().trackUpdate(
            propertyKey,
            duration,
            JSON.stringify(args).length
          );
        });
      }

      const duration = performance.now() - start;
      PerformanceMonitor.getInstance().trackUpdate(
        propertyKey,
        duration,
        JSON.stringify(args).length
      );

      return result;
    };

    return descriptor;
  };
}

// React component performance HOC
export function withPerformanceTracking<P extends object>(
  Component: React.ComponentType<P>,
  id: string
): React.ComponentType<P> {
  return class PerformanceTrackedComponent extends React.Component<P> {
    private renderStart: number = 0;

    componentDidMount() {
      const duration = performance.now() - this.renderStart;
      PerformanceMonitor.getInstance().trackRender(id, duration, 'mount');
    }

    componentDidUpdate() {
      const duration = performance.now() - this.renderStart;
      PerformanceMonitor.getInstance().trackRender(id, duration, 'update');
    }

    render() {
      this.renderStart = performance.now();
      return <Component {...this.props} />;
    }
  };
}

// Network performance tracking
export async function measureNetworkOperation<T>(
  type: 'sync' | 'persist' | 'load',
  operation: () => Promise<T>
): Promise<T> {
  const start = performance.now();
  const result = await operation();
  const duration = performance.now() - start;
  
  PerformanceMonitor.getInstance().trackNetwork(
    type,
    duration,
    JSON.stringify(result).length
  );

  return result;
} 