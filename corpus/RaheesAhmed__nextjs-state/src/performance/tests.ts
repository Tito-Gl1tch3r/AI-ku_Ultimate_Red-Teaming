import { PerformanceTestSuite } from './test-suite';
import { create } from '../core';

interface TestState {
  count: number;
  items: string[];
  nested: {
    value: number;
    data: Record<string, unknown>;
  };
}

const initialState: TestState = {
  count: 0,
  items: [],
  nested: {
    value: 0,
    data: {},
  },
};

export async function runPerformanceTests() {
  const suite = new PerformanceTestSuite();

  // Test cases
  const tests = [
    // Basic state update performance
    {
      name: 'Simple State Update',
      setup: () => {
        const store = create({ initialState });
        return Promise.resolve(store);
      },
      run: async () => {
        const store = create({ initialState });
        store.setState({ count: Math.random() });
      },
    },

    // Array manipulation performance
    {
      name: 'Array Updates',
      setup: () => {
        const store = create({ initialState });
        return Promise.resolve(store);
      },
      run: async () => {
        const store = create({ initialState });
        const items = Array.from({ length: 1000 }, (_, i) => `item-${i}`);
        store.setState({ items });
      },
    },

    // Nested state update performance
    {
      name: 'Nested State Update',
      setup: () => {
        const store = create({ initialState });
        return Promise.resolve(store);
      },
      run: async () => {
        const store = create({ initialState });
        store.setState({
          nested: {
            value: Math.random(),
            data: { [Date.now()]: Math.random() },
          },
        });
      },
    },

    // Multiple subscribers performance
    {
      name: 'Multiple Subscribers',
      setup: () => {
        const store = create({ initialState });
        // Add 100 subscribers
        for (let i = 0; i < 100; i++) {
          store.subscribe(() => {});
        }
        return Promise.resolve(store);
      },
      run: async () => {
        const store = create({ initialState });
        store.setState({ count: Math.random() });
      },
    },

    // Selector performance
    {
      name: 'Selector Computation',
      setup: () => {
        const store = create({ initialState });
        return Promise.resolve(store);
      },
      run: async () => {
        const store = create({ initialState });
        const items = Array.from({ length: 1000 }, (_, i) => `item-${i}`);
        store.setState({ items });
        
        // Complex selector
        const result = store.getState().items
          .filter(item => item.includes('5'))
          .map(item => item.toUpperCase())
          .reduce((acc, item) => acc + item.length, 0);
      },
    },

    // Batch update performance
    {
      name: 'Batch Updates',
      setup: () => {
        const store = create({ initialState });
        return Promise.resolve(store);
      },
      run: async () => {
        const store = create({ initialState });
        // Perform 100 updates in quick succession
        for (let i = 0; i < 100; i++) {
          store.setState({ count: i });
        }
      },
    },

    // Memory leak check
    {
      name: 'Memory Leak Check',
      setup: () => {
        const store = create({ initialState });
        return Promise.resolve(store);
      },
      run: async () => {
        const store = create({ initialState });
        const unsubscribers: Array<() => void> = [];
        
        // Add and remove many subscribers
        for (let i = 0; i < 1000; i++) {
          unsubscribers.push(store.subscribe(() => {}));
        }
        
        // Cleanup
        unsubscribers.forEach(unsub => unsub());
      },
    },

    // Storage performance
    {
      name: 'Storage Operations',
      setup: () => {
        const store = create({
          initialState,
          options: {
            storage: {
              key: 'test-storage',
              version: 1,
              migrations: {},
            },
          },
        });
        return Promise.resolve(store);
      },
      run: async () => {
        const store = create({
          initialState,
          options: {
            storage: {
              key: 'test-storage',
              version: 1,
              migrations: {},
            },
          },
        });
        
        // Perform storage operations
        await store.setState({ count: Math.random() });
      },
    },
  ];

  // Run tests
  const results = await suite.runTests(tests);

  // Print summary
  console.log('\nPerformance Test Summary');
  console.log('=======================');
  console.log(suite.generateReport());

  return results;
}

// Helper function to measure component render performance
export function measureComponentPerformance(
  Component: React.ComponentType,
  props: object = {}
) {
  return {
    name: `Component: ${Component.name}`,
    setup: () => {
      const container = document.createElement('div');
      document.body.appendChild(container);
      return Promise.resolve({ container });
    },
    run: async ({ container }: { container: HTMLElement }) => {
      const start = performance.now();
      // @ts-ignore
      ReactDOM.render(React.createElement(Component, props), container);
      await new Promise(resolve => setTimeout(resolve, 0)); // Wait for render
      return performance.now() - start;
    },
    teardown: async ({ container }: { container: HTMLElement }) => {
      // @ts-ignore
      ReactDOM.unmountComponentAtNode(container);
      container.remove();
    },
  };
} 