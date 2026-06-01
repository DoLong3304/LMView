import React, { useEffect, useState } from "react";
import { Loader2, X } from "lucide-react";
import { useAuth } from "@/features/auth/AuthContext";
import { useI18n } from "@/i18n";

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose }) => {
  const { login, register } = useAuth();
  const { t } = useI18n();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen) return;

    setMode("login");
    setName("");
    setEmail("");
    setPassword("");
    setConfirmPw("");
    setError("");
    setLoading(false);
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !loading) {
        onClose();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, loading, onClose]);

  if (!isOpen) return null;

  const handleBackdropMouseDown = (
    event: React.MouseEvent<HTMLDivElement>,
  ) => {
    if (event.target === event.currentTarget && !loading) {
      onClose();
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (mode === "register") {
      if (password !== confirmPw) {
        setError(t("passwordsMismatch"));
        return;
      }
      if (password.length < 6) {
        setError(t("passwordMinLength"));
        return;
      }
    }

    setLoading(true);
    try {
      const result =
        mode === "register"
          ? await register(name.trim(), email.trim(), password)
          : await login(email.trim(), password);

      if (!result.success) {
        setError(
          result.error
            ? t(result.error as Parameters<typeof t>[0])
            : t("somethingWentWrong"),
        );
        return;
      }
      onClose();
    } catch {
      setError(t("somethingWentWrong"));
    } finally {
      setLoading(false);
    }
  };

  const switchMode = () => {
    setMode(mode === "login" ? "register" : "login");
    setError("");
  };

  return (
    <div
      className="fixed inset-0 z-[500] flex items-center justify-center bg-black/55 px-4 backdrop-blur-sm"
      onMouseDown={handleBackdropMouseDown}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="auth-modal-title"
        className="relative w-full max-w-sm rounded border border-[var(--lm-border)] bg-[var(--lm-bg-secondary)] p-6 shadow-2xl"
      >
        <button
          type="button"
          onClick={onClose}
          className="absolute right-3 top-3 rounded p-1 text-gray-400 transition-colors hover:bg-gray-700 hover:text-white"
          title={t("close")}
          aria-label={t("close")}
        >
          <X size={20} />
        </button>

        <h2
          id="auth-modal-title"
          className="mb-6 text-xl font-bold text-[var(--lm-text-primary)]"
        >
          {mode === "login" ? t("loginTitle") : t("registerTitle")}
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === "register" && (
            <div>
              <label className="mb-1 block text-sm text-gray-400">
                {t("name")}
              </label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full rounded border border-[var(--lm-border)] bg-[var(--lm-bg-tertiary)] px-3 py-2 text-[var(--lm-text-primary)] outline-none transition-colors focus:border-blue-500"
                placeholder={t("name")}
                autoComplete="name"
                disabled={loading}
              />
            </div>
          )}
          <div>
            <label className="mb-1 block text-sm text-gray-400">
              {t("email")}
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded border border-[var(--lm-border)] bg-[var(--lm-bg-tertiary)] px-3 py-2 text-[var(--lm-text-primary)] outline-none transition-colors focus:border-blue-500"
              placeholder="email@example.com"
              autoComplete="email"
              disabled={loading}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-gray-400">
              {t("password")}
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded border border-[var(--lm-border)] bg-[var(--lm-bg-tertiary)] px-3 py-2 text-[var(--lm-text-primary)] outline-none transition-colors focus:border-blue-500"
              placeholder="******"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              disabled={loading}
            />
          </div>
          {mode === "register" && (
            <div>
              <label className="mb-1 block text-sm text-gray-400">
                {t("confirmPassword")}
              </label>
              <input
                type="password"
                required
                value={confirmPw}
                onChange={(e) => setConfirmPw(e.target.value)}
                className="w-full rounded border border-[var(--lm-border)] bg-[var(--lm-bg-tertiary)] px-3 py-2 text-[var(--lm-text-primary)] outline-none transition-colors focus:border-blue-500"
                placeholder="******"
                autoComplete="new-password"
                disabled={loading}
              />
            </div>
          )}

          {error && <p className="text-sm text-red-400">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="flex w-full items-center justify-center gap-2 rounded bg-blue-600 py-2 font-semibold text-white transition-colors hover:bg-blue-700 disabled:cursor-wait disabled:bg-blue-800"
          >
            {loading && <Loader2 size={16} className="animate-spin" />}
            {mode === "login" ? t("signIn") : t("signUp")}
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-gray-400">
          {mode === "login" ? t("noAccount") : t("hasAccount")}{" "}
          <button
            type="button"
            onClick={switchMode}
            className="text-blue-400 hover:text-blue-300 disabled:cursor-wait disabled:opacity-60"
            disabled={loading}
          >
            {mode === "login" ? t("signUp") : t("signIn")}
          </button>
        </p>
      </div>
    </div>
  );
};

export default AuthModal;
