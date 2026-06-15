import React, { Component, ErrorInfo, ReactNode } from "react";
import { normalizeError, sanitizeTechnicalDetails, type NormalizedError } from "@/utils/errors";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  isAdmin?: boolean;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
  normalizedError: NormalizedError | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null, errorInfo: null, normalizedError: null };

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
      errorInfo: null,
      normalizedError: normalizeError(error, { area: "general", fallbackCode: "UNKNOWN_CRASH" }),
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    const componentTrace = sanitizeTechnicalDetails(errorInfo.componentStack || "");
    if (this.props.isAdmin || process.env.NODE_ENV === "development") {
      console.error("[ErrorBoundary] Caught error:", sanitizeTechnicalDetails(error), componentTrace);
    }
    this.setState({
      errorInfo,
      normalizedError: normalizeError(error, {
        area: "general",
        fallbackCode: "UNKNOWN_CRASH",
        technicalDetails: [
          error.stack || error.message,
          componentTrace ? `Component trace: ${componentTrace}` : "",
        ].filter(Boolean).join("\n"),
      }),
    });
    this.props.onError?.(error, errorInfo);
  }

  reset(): void {
    this.setState({ hasError: false, error: null, errorInfo: null, normalizedError: null });
  }

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      const normalized = this.state.normalizedError ?? normalizeError(this.state.error, {
        area: "general",
        fallbackCode: "UNKNOWN_CRASH",
      });
      const isAdmin = Boolean(this.props.isAdmin);

      return (
        <div className="flex flex-col items-center justify-center min-h-[200px] p-6 bg-red-950/20 border border-red-800/40 rounded-lg">
          <h2 className="text-lg font-bold text-red-400 mb-2">
            Something went wrong
          </h2>
          <p className="text-sm text-gray-400 mb-4 max-w-md">
            {normalized.code} An unexpected error occurred. Please try again.
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
          {isAdmin && (
            <details className="mt-4 w-full max-w-2xl rounded border border-gray-800 bg-gray-900/80 p-3 text-left">
              <summary className="cursor-pointer text-xs font-semibold text-gray-300">
                Technical details
              </summary>
              <pre className="mt-3 max-h-40 overflow-auto whitespace-pre-wrap text-xs leading-5 text-gray-400">
                {normalized.adminMessage}
              </pre>
            </details>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}
