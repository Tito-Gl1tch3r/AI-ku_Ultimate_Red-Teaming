import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { createNextState } from '../core';
import { useSelector } from '../hooks';

interface TestState {
  count: number;
  items: Array<{ id: number; value: string }>;
}

describe('Performance Tests', () => {
  describe('State Update Performance', () => {
    it('should handle rapid updates efficiently', () => {
      const { useNextState } = createNextState<TestState>({
        initialState: {
          count: 0,
          items: [],
        },
      });

      const { result } = renderHook(() => useNextState());
      const iterations = 1000;
      const start = performance.now();

      act(() => {
        for (let i = 0; i < iterations; i++) {
          result.current.setState({ count: i, items: [] });
        }
      });

      const end = performance.now();
      const duration = end - start;

      expect(duration).toBeLessThan(1000); // Should complete in less than 1s
      expect(result.current.state.count).toBe(iterations - 1);
    });

    it('should handle large state updates efficiently', () => {
      const largeState: TestState = {
        count: 0,
        items: Array.from({ length: 1000 }, (_, i) => ({
          id: i,
          value: `Item ${i}`,
        })),
      };

      const { useNextState } = createNextState<TestState>({
        initialState: largeState,
      });

      const { result } = renderHook(() => useNextState());
      const start = performance.now();

      act(() => {
        result.current.setState({
          ...largeState,
          items: largeState.items.map((item) => ({
            ...item,
            value: `Updated ${item.value}`,
          })),
        });
      });

      const end = performance.now();
      const duration = end - start;

      expect(duration).toBeLessThan(100); // Should complete in less than 100ms
      expect(result.current.state.items[0].value).toContain('Updated');
    });
  });

  describe('Selector Performance', () => {
    it('should memoize selectors efficiently', () => {
      const { useNextState } = createNextState<TestState>({
        initialState: {
          count: 0,
          items: Array.from({ length: 100 }, (_, i) => ({
            id: i,
            value: `Item ${i}`,
          })),
        },
      });

      const { result } = renderHook(() => {
        const state = useNextState();
        return {
          state,
          selected: useSelector(state, (s) => s.items.find((item) => item.id === 50)),
        };
      });

      const initialSelected = result.current.selected;

      act(() => {
        result.current.state.setState((prev) => ({ ...prev, count: prev.count + 1 }));
      });

      expect(result.current.selected).toBe(initialSelected); // Reference equality check
    });
  });
});
