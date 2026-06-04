import React from "react";
import { AlertTriangle } from "lucide-react";
import translations, { type TranslationKey } from "@/i18n/translations";

interface ErrorBoundaryProps {
  children: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

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
      return (
        <div className="min-h-screen bg-gray-900 flex items-center justify-center p-8">
          <div className="bg-gray-800 rounded-xl border border-red-500/30 p-8 max-w-md w-full text-center">
            <AlertTriangle className="text-red-400 w-10 h-10 mb-4 mx-auto" />
            <h1 className="text-xl font-bold text-white mb-2">
              {this.t("somethingWentWrong")}
            </h1>
            <p className="text-gray-400 text-sm mb-6">
              {this.state.error?.message || this.t("unexpectedError")}
            </p>
            <button
              onClick={this.handleReset}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
            >
              {this.t("tryAgain")}
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
