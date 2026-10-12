import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { createNextState } from '../core';

interface TestState {
  count: number;
}

describe('Core State Management', () => {
  it('should initialize with default state', () => {
    const { useNextState } = createNextState<TestState>({
      initialState: { count: 0 },
    });

    const { result } = renderHook(() => useNextState());
    expect(result.current.state.count).toBe(0);
  });

  it('should update state when setState is called', () => {
    const { useNextState } = createNextState<TestState>({
      initialState: { count: 0 },
    });

    const { result } = renderHook(() => useNextState());

    act(() => {
      result.current.setState({ count: 1 });
    });

    expect(result.current.state.count).toBe(1);
  });

  it('should support functional updates', () => {
    const { useNextState } = createNextState<TestState>({
      initialState: { count: 0 },
    });

    const { result } = renderHook(() => useNextState());

    act(() => {
      result.current.setState((prev) => ({ count: prev.count + 1 }));
    });

    expect(result.current.state.count).toBe(1);
  });
});
