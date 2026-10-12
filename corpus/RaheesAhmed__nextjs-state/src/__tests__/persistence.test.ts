import { describe, it, expect, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { createNextState } from '../core';
import { createPersistenceMiddleware } from '../middleware';

interface TestState {
  count: number;
}

describe('Persistence', () => {
  it('should persist state to localStorage', () => {
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

  it('should handle localStorage errors gracefully', () => {
    const setItemSpy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('Storage quota exceeded');
    });

    const persistenceMiddleware = createPersistenceMiddleware<TestState>('test-state');

    const { useNextState } = createNextState<TestState>({
      initialState: { count: 0 },
      middleware: [persistenceMiddleware],
    });

    const { result } = renderHook(() => useNextState());

    expect(() => {
      act(() => {
        result.current.setState({ count: 1 });
      });
    }).not.toThrow();

    setItemSpy.mockRestore();
  });
});
