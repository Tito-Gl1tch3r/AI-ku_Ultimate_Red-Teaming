import { describe, it, expect, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { createNextState } from '../core';
import { createLoggingMiddleware, createPersistenceMiddleware } from '../middleware';

interface TestState {
  count: number;
}

describe('Middleware', () => {
  it('should apply logging middleware', () => {
    const consoleSpy = vi.spyOn(console, 'log');
    const loggingMiddleware = createLoggingMiddleware<TestState>();

    const { useNextState } = createNextState<TestState>({
      initialState: { count: 0 },
      middleware: [loggingMiddleware],
    });

    const { result } = renderHook(() => useNextState());

    act(() => {
      result.current.setState({ count: 1 });
    });

    expect(consoleSpy).toHaveBeenCalledWith('Previous state:', { count: 0 });
    expect(consoleSpy).toHaveBeenCalledWith('Next state:', { count: 1 });
    consoleSpy.mockRestore();
  });

  it('should apply persistence middleware', () => {
    const setItemSpy = vi.spyOn(Storage.prototype, 'setItem');
    const persistenceMiddleware = createPersistenceMiddleware<TestState>('test-state');

    const { useNextState } = createNextState<TestState>({
      initialState: { count: 0 },
      middleware: [persistenceMiddleware],
    });

    const { result } = renderHook(() => useNextState());

    act(() => {
      result.current.setState({ count: 1 });
    });

    expect(setItemSpy).toHaveBeenCalledWith('test-state', JSON.stringify({ count: 1 }));
    setItemSpy.mockRestore();
  });
});
