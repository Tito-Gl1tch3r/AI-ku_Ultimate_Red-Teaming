import React from 'react';

export class NextStateError extends Error {
  constructor(
    message: string,
    public readonly code: string = 'UNKNOWN_ERROR',
    public readonly details?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'NextStateError';
  }
}

export class NextStateErrorBoundary extends React.Component<
  { fallback?: React.ReactNode; children: React.ReactNode },
  { hasError: boolean; error?: NextStateError }
> {
  constructor(props: { fallback?: React.ReactNode; children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: NextStateError) {
    return { hasError: true, error };
  }

  componentDidCatch(error: NextStateError, errorInfo: React.ErrorInfo) {
    console.error('NextState Error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <div role="alert" className="next-state-error">
            <h2>Something went wrong with state management</h2>
            <pre>{this.state.error?.message}</pre>
          </div>
        )
      );
    }

    return this.props.children;
  }
}
