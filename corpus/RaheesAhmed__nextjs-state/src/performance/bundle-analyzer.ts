import { gzipSync } from 'zlib';
import { readFileSync } from 'fs';
import { join } from 'path';

interface BundleStats {
  raw: number;
  gzip: number;
  modules: Array<{
    name: string;
    size: number;
    gzipSize: number;
    percentage: number;
  }>;
  totalModules: number;
  date: string;
}

interface ModuleInfo {
  id: string;
  name: string;
  size: number;
  code: string;
}

export class BundleAnalyzer {
  private static readonly SIZE_LIMIT = 4 * 1024; // 4KB
  private history: BundleStats[] = [];

  constructor(private distPath: string) {}

  async analyze(): Promise<BundleStats> {
    const files = this.getJsFiles();
    const modules = await this.analyzeModules(files);
    const totalSize = modules.reduce((sum, mod) => sum + mod.size, 0);
    const gzipSize = this.calculateGzipSize(modules);

    const stats: BundleStats = {
      raw: totalSize,
      gzip: gzipSize,
      modules: modules.map(mod => ({
        name: mod.name,
        size: mod.size,
        gzipSize: this.getGzipSize(mod.code),
        percentage: (mod.size / totalSize) * 100,
      })),
      totalModules: modules.length,
      date: new Date().toISOString(),
    };

    this.history.push(stats);
    this.checkSizeLimits(stats);

    return stats;
  }

  private getJsFiles(): string[] {
    try {
      const files = readFileSync(join(this.distPath, 'stats.json'), 'utf-8');
      const stats = JSON.parse(files);
      return stats.assets
        .filter((asset: any) => asset.name.endsWith('.js'))
        .map((asset: any) => join(this.distPath, asset.name));
    } catch (error) {
      console.error('Failed to read bundle stats:', error);
      return [];
    }
  }

  private async analyzeModules(files: string[]): Promise<ModuleInfo[]> {
    const modules: ModuleInfo[] = [];

    for (const file of files) {
      try {
        const content = readFileSync(file, 'utf-8');
        const moduleInfo = this.parseModuleInfo(content);
        modules.push(...moduleInfo);
      } catch (error) {
        console.error(`Failed to analyze ${file}:`, error);
      }
    }

    return modules;
  }

  private parseModuleInfo(content: string): ModuleInfo[] {
    const modules: ModuleInfo[] = [];
    const moduleRegex = /\/\*\* MODULE \[(.*?)\] \*\/([\s\S]*?)\/\*\* END_MODULE \*\//g;
    
    let match;
    while ((match = moduleRegex.exec(content)) !== null) {
      const [, id, code] = match;
      modules.push({
        id,
        name: this.getModuleName(id),
        size: code.length,
        code,
      });
    }

    return modules;
  }

  private getModuleName(id: string): string {
    // Convert module ID to readable name
    return id
      .split('/')
      .pop()!
      .replace(/\.[^/.]+$/, '');
  }

  private calculateGzipSize(modules: ModuleInfo[]): number {
    const concatenatedCode = modules.map(m => m.code).join('');
    return this.getGzipSize(concatenatedCode);
  }

  private getGzipSize(content: string): number {
    return gzipSync(content).length;
  }

  private checkSizeLimits(stats: BundleStats): void {
    if (stats.gzip > BundleAnalyzer.SIZE_LIMIT) {
      console.warn(
        `Bundle size (${(stats.gzip / 1024).toFixed(2)}KB) exceeds limit (${
          BundleAnalyzer.SIZE_LIMIT / 1024
        }KB)`
      );
      this.suggestOptimizations(stats);
    }
  }

  private suggestOptimizations(stats: BundleStats): void {
    console.log('\nOptimization Suggestions:');

    // Find large modules
    const largeModules = stats.modules
      .filter(m => m.gzipSize > 1024) // > 1KB
      .sort((a, b) => b.size - a.size);

    if (largeModules.length > 0) {
      console.log('\nLarge Modules:');
      largeModules.forEach(m => {
        console.log(
          `- ${m.name}: ${(m.gzipSize / 1024).toFixed(2)}KB (${m.percentage.toFixed(
            1
          )}%)`
        );
      });
    }

    // Check for duplicate modules
    const duplicates = this.findDuplicateModules(stats.modules);
    if (duplicates.length > 0) {
      console.log('\nDuplicate Modules:');
      duplicates.forEach(([name, count]) => {
        console.log(`- ${name} appears ${count} times`);
      });
    }

    // Suggest code splitting
    if (stats.gzip > 50 * 1024) { // 50KB
      console.log('\nConsider Code Splitting:');
      console.log('- Use dynamic imports for large features');
      console.log('- Split vendor and application code');
      console.log('- Implement route-based code splitting');
    }
  }

  private findDuplicateModules(modules: BundleStats['modules']): [string, number][] {
    const counts = new Map<string, number>();
    
    modules.forEach(m => {
      const count = counts.get(m.name) || 0;
      counts.set(m.name, count + 1);
    });

    return Array.from(counts.entries())
      .filter(([, count]) => count > 1)
      .sort(([, a], [, b]) => b - a);
  }

  getHistory(): BundleStats[] {
    return this.history;
  }

  compareWithBaseline(baseline: BundleStats): {
    totalDiff: number;
    gzipDiff: number;
    moduleDiffs: Array<{
      name: string;
      sizeDiff: number;
      gzipDiff: number;
    }>;
  } {
    const latest = this.history[this.history.length - 1];
    if (!latest) throw new Error('No bundle analysis available');

    return {
      totalDiff: latest.raw - baseline.raw,
      gzipDiff: latest.gzip - baseline.gzip,
      moduleDiffs: latest.modules.map(mod => {
        const baseModule = baseline.modules.find(m => m.name === mod.name);
        return {
          name: mod.name,
          sizeDiff: baseModule ? mod.size - baseModule.size : mod.size,
          gzipDiff: baseModule ? mod.gzipSize - baseModule.gzipSize : mod.gzipSize,
        };
      }),
    };
  }

  generateReport(): string {
    const latest = this.history[this.history.length - 1];
    if (!latest) return 'No bundle analysis available';

    return `
Bundle Size Report (${latest.date})
==================================

Total Size: ${(latest.raw / 1024).toFixed(2)}KB
Gzipped Size: ${(latest.gzip / 1024).toFixed(2)}KB
Total Modules: ${latest.totalModules}

Top 5 Largest Modules:
${latest.modules
  .sort((a, b) => b.size - a.size)
  .slice(0, 5)
  .map(
    m =>
      `- ${m.name}: ${(m.size / 1024).toFixed(2)}KB (${m.percentage.toFixed(1)}%)`
  )
  .join('\n')}

Size Status: ${latest.gzip <= BundleAnalyzer.SIZE_LIMIT ? '✅ Within Limit' : '❌ Exceeds Limit'}
`.trim();
  }
} 