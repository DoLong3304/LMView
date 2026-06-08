import React, { Component, ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null, errorInfo: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error("[ErrorBoundary] Caught error:", error, errorInfo);
    this.setState({ errorInfo });
    this.props.onError?.(error, errorInfo);
  }

  reset(): void {
    this.setState({ hasError: false, error: null, errorInfo: null });
  }

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;

      return (
        <div className="flex flex-col items-center justify-center min-h-[200px] p-6 bg-red-950/20 border border-red-800/40 rounded-lg">
          <h2 className="text-lg font-bold text-red-400 mb-2">
            Something went wrong
          </h2>
          <p className="text-sm text-gray-400 mb-4 max-w-md">
            {this.state.error?.message || "An unexpected error occurred"}
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => this.reset()}
              className="px-3 py-1.5 text-sm font-medium bg-red-600/80 hover:bg-red-500 text-white rounded transition-colors"
            >
              Retry
            </button>
            <button
              onClick={() => window.location.reload()}
              className="px-3 py-1.5 text-sm font-medium border border-gray-600 hover:border-gray-500 text-gray-300 rounded transition-colors"
            >
              Reload Page
            </button>
          </div>
          {process.env.NODE_ENV === "development" && this.state.error?.stack && (
            <pre className="mt-4 p-2 bg-gray-900/80 text-xs text-gray-400 overflow-auto max-w-full max-h-32 rounded">
              {this.state.error.stack}
            </pre>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}