import React from "react";
import { AlertTriangle } from "lucide-react";
import translations, { type TranslationKey } from "@/i18n/translations";
import { normalizeError, sanitizeTechnicalDetails, type NormalizedError } from "@/utils/errors";

interface ErrorBoundaryProps {
  children: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  normalizedError: NormalizedError | null;
  componentStack: string;
}

class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null, normalizedError: null, componentStack: "" };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return {
      hasError: true,
      error,
      normalizedError: normalizeError(error, { area: "general", fallbackCode: "UNKNOWN_CRASH" }),
      componentStack: "",
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    const componentStack = sanitizeTechnicalDetails(errorInfo.componentStack || "");
    if (this.isAdmin() || process.env.NODE_ENV === "development") {
      console.error("[RootErrorBoundary]", sanitizeTechnicalDetails(error), componentStack);
    }
    this.setState({
      componentStack,
      normalizedError: normalizeError(error, {
        area: "general",
        fallbackCode: "UNKNOWN_CRASH",
        technicalDetails: [
          error.stack || error.message,
          componentStack ? `Component trace: ${componentStack}` : "",
        ].filter(Boolean).join("\n"),
      }),
    });
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, normalizedError: null, componentStack: "" });
  };

  isAdmin(): boolean {
    try {
      return localStorage.getItem("lmview_auth_role") === "admin";
    } catch {
      return false;
    }
  }

  t(key: TranslationKey): string {
    try {
      const lang = localStorage.getItem("app_lang") || "en";
      const langTranslations = translations[
        lang as keyof typeof translations
      ] as Partial<Record<TranslationKey, string>> | undefined;
      return langTranslations?.[key] || translations.en[key] || key;
    } catch {
      return translations.en[key] || key;
    }
  }

  render() {
    if (this.state.hasError) {
      const normalized = this.state.normalizedError ?? normalizeError(this.state.error, {
        area: "general",
        fallbackCode: "UNKNOWN_CRASH",
      });
      const isAdmin = this.isAdmin();
      return (
        <div className="min-h-screen bg-gray-900 flex items-center justify-center p-8">
          <div className="bg-gray-800 rounded-xl border border-red-500/30 p-8 max-w-xl w-full text-center">
            <AlertTriangle className="text-red-400 w-10 h-10 mb-4 mx-auto" />
            <h1 className="text-xl font-bold text-white mb-2">
              {this.t("somethingWentWrong")}
            </h1>
            <p className="text-gray-400 text-sm mb-6">
              {normalized.code} {this.t("unexpectedError")}
            </p>
            <div className="flex justify-center gap-2">
              <button
                onClick={this.handleReset}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
              >
                {this.t("tryAgain")}
              </button>
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-2 border border-gray-600 hover:border-gray-500 text-gray-300 rounded-lg text-sm font-medium transition-colors"
              >
                {this.t("reloadPage")}
              </button>
            </div>
            {isAdmin && (
              <details className="mt-5 rounded border border-gray-700 bg-gray-900 p-3 text-left">
                <summary className="cursor-pointer text-xs font-semibold text-gray-300">
                  {this.t("technicalDetails")}
                </summary>
                <pre className="mt-3 max-h-48 overflow-auto whitespace-pre-wrap text-xs leading-5 text-gray-400">
                  {normalized.adminMessage}
                </pre>
              </details>
            )}
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
