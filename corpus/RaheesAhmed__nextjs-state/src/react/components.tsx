import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useMemo,
  Suspense,
  Component,
  type PropsWithChildren,
  type ErrorInfo,
} from 'react';
import type { DeepPartial } from '../types/types';
import { StateContext } from './context';

interface NextStateProviderProps<T extends object> {
  store: {
    getState: () => T;
    setState: (update: DeepPartial<T>) => void;
    subscribe: (listener: (state: T) => void) => () => void;
    getInitialState: () => T;
  };
  loading?: React.ReactNode;
  children: React.ReactNode;
}

/**
 * Provider component with Suspense integration
 */
export function NextStateProvider<T extends object>({
  store,
  loading = null,
  children,
}: NextStateProviderProps<T>) {
  const [isHydrated, setIsHydrated] = useState(false);

  useEffect(() => {
    setIsHydrated(true);
  }, []);

  const contextValue = useMemo(() => store, [store]);

  if (!isHydrated) {
    return loading;
  }

  return (
    <StateContext.Provider value={contextValue}>
      <Suspense fallback={loading}>{children}</Suspense>
    </StateContext.Provider>
  );
}

interface ErrorBoundaryState {
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

interface ErrorBoundaryProps extends PropsWithChildren {
  fallback?: React.ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  resetKeys?: any[];
}

/**
 * Error boundary for state management errors
 */
export class NextStateErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error, errorInfo: null };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    this.setState({ errorInfo });
    this.props.onError?.(error, errorInfo);
  }

  componentDidUpdate(prevProps: ErrorBoundaryProps): void {
    if (this.state.error && this.props.resetKeys) {
      if (prevProps.resetKeys?.some((key, i) => key !== this.props.resetKeys?.[i])) {
        this.setState({ error: null, errorInfo: null });
      }
    }
  }

  render(): React.ReactNode {
    if (this.state.error) {
      return (
        this.props.fallback || (
          <div style={{ padding: '20px', color: 'red' }}>
            <h2>Something went wrong</h2>
            <details style={{ whiteSpace: 'pre-wrap' }}>
              {this.state.error.toString()}
              <br />
              {this.state.errorInfo?.componentStack}
            </details>
          </div>
        )
      );
    }

    return this.props.children;
  }
}

interface SuspenseState {
  promise: Promise<any> | null;
  result: any;
}

const SuspenseContext = createContext<SuspenseState | null>(null);

/**
 * Suspense integration for async state updates
 */
export function NextStateSuspense({ children }: PropsWithChildren) {
  const [state] = useState<SuspenseState>(() => ({
    promise: null,
    result: null,
  }));

  return <SuspenseContext.Provider value={state}>{children}</SuspenseContext.Provider>;
}

/**
 * Hook to use suspense for async operations
 */
export function useSuspenseState<T>(promise: Promise<T>): T {
  const suspense = useContext(SuspenseContext);
  if (!suspense) {
    throw new Error('useSuspenseState must be used within NextStateSuspense');
  }

  if (suspense.promise === promise) {
    if (suspense.result) {
      return suspense.result;
    }
    throw promise;
  }

  suspense.promise = promise;
  throw promise.then((result) => {
    suspense.result = result;
  });
}

/**
 * HOC to wrap components with error boundary
 */
export function withNextStateErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  options: Omit<ErrorBoundaryProps, 'children'> = {}
) {
  return function WithErrorBoundary(props: P) {
    return (
      <NextStateErrorBoundary {...options}>
        <Component {...props} />
      </NextStateErrorBoundary>
    );
  };
}

/**
 * HOC to wrap components with suspense
 */
export function withNextStateSuspense<P extends object>(
  Component: React.ComponentType<P>,
  fallback: React.ReactNode = null
) {
  return function WithSuspense(props: P) {
    return (
      <Suspense fallback={fallback}>
        <NextStateSuspense>
          <Component {...props} />
        </NextStateSuspense>
      </Suspense>
    );
  };
}
