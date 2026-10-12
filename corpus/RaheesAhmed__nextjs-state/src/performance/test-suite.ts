import { PerformanceMonitor } from './monitor';
import { BundleAnalyzer } from './bundle-analyzer';

interface TestCase {
  name: string;
  setup?: () => Promise<void>;
  run: () => Promise<void>;
  teardown?: () => Promise<void>;
  iterations?: number;
}

interface TestResult {
  name: string;
  averageTime: number;
  minTime: number;
  maxTime: number;
  medianTime: number;
  p95Time: number;
  memoryUsage: {
    before: number;
    after: number;
    diff: number;
  };
  renderCount: number;
  networkCalls: number;
}

export class PerformanceTestSuite {
  private monitor = PerformanceMonitor.getInstance();
  private analyzer: BundleAnalyzer;
  private results: TestResult[] = [];

  constructor(distPath: string) {
    this.analyzer = new BundleAnalyzer(distPath);
  }

  async runTests(tests: TestCase[]): Promise<TestResult[]> {
    console.log('\nRunning Performance Tests...\n');

    for (const test of tests) {
      const result = await this.runTest(test);
      this.results.push(result);
      this.printTestResult(result);
    }

    await this.analyzeBundleSize();
    this.generateReport();

    return this.results;
  }

  private async runTest(test: TestCase): Promise<TestResult> {
    const iterations = test.iterations || 100;
    const times: number[] = [];
    let totalRenderCount = 0;
    let totalNetworkCalls = 0;

    // Setup
    if (test.setup) {
      await test.setup();
    }

    // Measure memory before
    const memoryBefore = process.memoryUsage().heapUsed;

    // Run test iterations
    for (let i = 0; i < iterations; i++) {
      this.monitor.reset();
      const start = performance.now();

      await test.run();

      const duration = performance.now() - start;
      times.push(duration);

      // Collect metrics
      const metrics = this.monitor.getMetrics();
      totalRenderCount += metrics.renders?.length || 0;
      totalNetworkCalls += metrics.network?.operationCount || 0;
    }

    // Measure memory after
    const memoryAfter = process.memoryUsage().heapUsed;

    // Teardown
    if (test.teardown) {
      await test.teardown();
    }

    // Calculate statistics
    times.sort((a, b) => a - b);
    const averageTime = times.reduce((a, b) => a + b, 0) / times.length;
    const minTime = times[0];
    const maxTime = times[times.length - 1];
    const medianTime = times[Math.floor(times.length / 2)];
    const p95Time = times[Math.floor(times.length * 0.95)];

    return {
      name: test.name,
      averageTime,
      minTime,
      maxTime,
      medianTime,
      p95Time,
      memoryUsage: {
        before: memoryBefore,
        after: memoryAfter,
        diff: memoryAfter - memoryBefore,
      },
      renderCount: totalRenderCount / iterations,
      networkCalls: totalNetworkCalls / iterations,
    };
  }

  private async analyzeBundleSize(): Promise<void> {
    console.log('\nAnalyzing Bundle Size...\n');
    const stats = await this.analyzer.analyze();
    console.log(this.analyzer.generateReport());

    if (stats.gzip > 4 * 1024) {
      console.warn('\n⚠️ Bundle size exceeds 4KB target!');
      console.log('Suggestions for optimization:');
      console.log('1. Use tree shaking');
      console.log('2. Implement code splitting');
      console.log('3. Remove unused dependencies');
      console.log('4. Minify and compress assets');
    }
  }

  private printTestResult(result: TestResult): void {
    console.log(`\nTest: ${result.name}`);
    console.log('----------------------------------------');
    console.log(`Average Time: ${result.averageTime.toFixed(2)}ms`);
    console.log(`Min Time: ${result.minTime.toFixed(2)}ms`);
    console.log(`Max Time: ${result.maxTime.toFixed(2)}ms`);
    console.log(`Median Time: ${result.medianTime.toFixed(2)}ms`);
    console.log(`95th Percentile: ${result.p95Time.toFixed(2)}ms`);
    console.log(`Memory Impact: ${(result.memoryUsage.diff / 1024 / 1024).toFixed(2)}MB`);
    console.log(`Average Render Count: ${result.renderCount.toFixed(1)}`);
    console.log(`Average Network Calls: ${result.networkCalls.toFixed(1)}`);
  }

  generateReport(): string {
    const report = ['Performance Test Report', '======================\n'];

    // Overall Statistics
    const totalTests = this.results.length;
    const slowTests = this.results.filter(r => r.p95Time > 100).length;
    const memoryIntensive = this.results.filter(
      r => r.memoryUsage.diff > 5 * 1024 * 1024
    ).length;

    report.push(`Total Tests: ${totalTests}`);
    report.push(`Slow Tests (>100ms): ${slowTests}`);
    report.push(`Memory Intensive Tests (>5MB): ${memoryIntensive}\n`);

    // Performance Breakdown
    report.push('Performance Breakdown:');
    report.push('--------------------');
    this.results.forEach(result => {
      report.push(`\n${result.name}:`);
      report.push(`  Average: ${result.averageTime.toFixed(2)}ms`);
      report.push(`  P95: ${result.p95Time.toFixed(2)}ms`);
      report.push(`  Memory: ${(result.memoryUsage.diff / 1024 / 1024).toFixed(2)}MB`);
      report.push(`  Renders: ${result.renderCount.toFixed(1)}`);
      report.push(`  Network: ${result.networkCalls.toFixed(1)} calls`);
    });

    // Recommendations
    report.push('\nRecommendations:');
    report.push('---------------');

    if (slowTests > 0) {
      report.push('- Optimize slow tests:');
      this.results
        .filter(r => r.p95Time > 100)
        .forEach(r => {
          report.push(`  * ${r.name} (${r.p95Time.toFixed(2)}ms)`);
        });
    }

    if (memoryIntensive > 0) {
      report.push('- Reduce memory usage in:');
      this.results
        .filter(r => r.memoryUsage.diff > 5 * 1024 * 1024)
        .forEach(r => {
          report.push(
            `  * ${r.name} (${(r.memoryUsage.diff / 1024 / 1024).toFixed(2)}MB)`
          );
        });
    }

    const highRenderTests = this.results.filter(r => r.renderCount > 2);
    if (highRenderTests.length > 0) {
      report.push('- Reduce unnecessary renders in:');
      highRenderTests.forEach(r => {
        report.push(`  * ${r.name} (${r.renderCount.toFixed(1)} renders)`);
      });
    }

    return report.join('\n');
  }

  // Helper method to create common test cases
  static createTestCase(options: {
    name: string;
    component: React.ComponentType;
    props?: object;
    interactions?: Array<() => Promise<void>>;
    iterations?: number;
  }): TestCase {
    return {
      name: options.name,
      iterations: options.iterations,
      setup: async () => {
        // Setup test environment
        const container = document.createElement('div');
        document.body.appendChild(container);
        ReactDOM.render(
          React.createElement(options.component, options.props),
          container
        );
        await new Promise(resolve => setTimeout(resolve, 100)); // Wait for initial render
      },
      run: async () => {
        if (options.interactions) {
          for (const interaction of options.interactions) {
            await interaction();
          }
        }
      },
      teardown: async () => {
        // Cleanup
        document.body.innerHTML = '';
      },
    };
  }
}