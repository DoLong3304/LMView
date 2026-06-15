import React, { useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Loader2,
  LockKeyhole,
  Mail,
  UserRound,
  X,
} from "lucide-react";
import { useAuth } from "@/features/auth/AuthContext";
import { useI18n } from "@/i18n";
import type { TranslationKey } from "@/i18n/translations";

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
}

type AuthFieldKey = "name" | "email" | "password" | "confirmPw";
type AuthFieldErrors = Partial<Record<AuthFieldKey, string>>;

const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose }) => {
  const { login, register } = useAuth();
  const { t } = useI18n();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [fieldErrors, setFieldErrors] = useState<AuthFieldErrors>({});
  const [loading, setLoading] = useState(false);
  const isRegister = mode === "register";

  useEffect(() => {
    if (isOpen) return;

    setMode("login");
    setName("");
    setEmail("");
    setPassword("");
    setConfirmPw("");
    setError("");
    setSuccess("");
    setFieldErrors({});
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

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");
    setSuccess("");

    const nextFieldErrors = validateAuthForm({
      isRegister,
      name,
      email,
      password,
      confirmPw,
      t,
    });
    setFieldErrors(nextFieldErrors);
    if (Object.keys(nextFieldErrors).length > 0) {
      setError(t("checkFormFields"));
      return;
    }

    setLoading(true);
    try {
      const result = isRegister
        ? await register(name.trim(), email.trim(), password)
        : await login(email.trim(), password);

      if (!result.success) {
        setError(formatAuthError(result.error, t));
        return;
      }
      setSuccess(isRegister ? t("registerSuccess") : t("loginSuccess"));
      await new Promise((resolve) => window.setTimeout(resolve, 350));
      onClose();
    } catch {
      setError(t("somethingWentWrong"));
    } finally {
      setLoading(false);
    }
  };

  const switchMode = () => {
    setMode(isRegister ? "login" : "register");
    setError("");
    setSuccess("");
    setFieldErrors({});
  };

  const clearFieldError = (field: AuthFieldKey) => {
    setFieldErrors((current) => {
      if (!current[field]) return current;
      const next = { ...current };
      delete next[field];
      return next;
    });
  };

  return (
    <div
      className="fixed inset-0 z-[500] flex items-end justify-center bg-black/65 px-0 py-0 backdrop-blur-sm sm:items-center sm:px-3 sm:py-6"
      onMouseDown={handleBackdropMouseDown}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="auth-modal-title"
        className="relative grid max-h-[calc(100dvh-0.75rem)] w-full max-w-3xl overflow-hidden rounded-t border border-gray-700 bg-gray-950 text-gray-100 shadow-2xl sm:max-h-[92vh] sm:rounded md:grid-cols-[0.85fr_1.15fr]"
      >
        <section className="hidden border-r border-gray-800 bg-gray-900 p-6 md:block">
          <div className="flex h-11 w-11 items-center justify-center rounded border border-blue-500/30 bg-blue-500/15 text-blue-100">
            <LockKeyhole size={21} />
          </div>
          <h2 id="auth-modal-title" className="mt-5 text-xl font-semibold text-white">
            {isRegister ? t("registerTitle") : t("loginTitle")}
          </h2>
          <p className="mt-2 text-sm leading-6 text-gray-400">
            {isRegister ? t("registerSubtitle") : t("loginSubtitle")}
          </p>
          <div className="mt-6 space-y-3 text-xs text-gray-400">
            <AuthBenefit text={t("authBenefitSettings")} />
            <AuthBenefit text={t("authBenefitAi")} />
            <AuthBenefit text={t("authBenefitSecurity")} />
          </div>
        </section>

        <section className="flex min-h-0 min-w-0 flex-col overflow-hidden">
          <div className="flex flex-shrink-0 items-start justify-between gap-4 border-b border-gray-800 px-4 py-4 sm:px-6">
            <div className="min-w-0 md:hidden">
              <div className="mb-3 flex h-10 w-10 items-center justify-center rounded border border-blue-500/30 bg-blue-500/15 text-blue-100">
                <LockKeyhole size={19} />
              </div>
              <h2 className="text-xl font-semibold text-white">
                {isRegister ? t("registerTitle") : t("loginTitle")}
              </h2>
              <p className="mt-1 max-w-lg text-sm leading-6 text-gray-400">
                {isRegister ? t("registerSubtitle") : t("loginSubtitle")}
              </p>
            </div>
            <div className="hidden min-w-0 md:block">
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                LMView
              </p>
              <p className="mt-1 text-sm text-gray-400">
                {isRegister ? t("registerTitle") : t("loginTitle")}
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded border border-gray-700/80 bg-gray-950/85 text-gray-400 shadow-sm transition-colors hover:border-red-400/80 hover:bg-red-500/10 hover:text-red-300 focus:outline-none focus:ring-2 focus:ring-red-400/70 focus:ring-offset-2 focus:ring-offset-gray-950 disabled:cursor-wait disabled:opacity-60"
              title={t("close")}
              aria-label={t("close")}
              disabled={loading}
            >
              <X size={18} />
            </button>
          </div>

          <div className="min-h-0 overflow-y-auto px-4 pb-5 pt-5 sm:p-6">
            <div className="mb-5 grid grid-cols-2 rounded border border-gray-800 bg-gray-900 p-1">
              <button
                type="button"
                onClick={() => {
                  setMode("login");
                  setError("");
                }}
                disabled={loading}
                className={`rounded px-3 py-2 text-sm font-semibold transition-colors ${
                  !isRegister ? "bg-blue-600 text-white" : "text-gray-400 hover:text-white"
                }`}
              >
                {t("signIn")}
              </button>
              <button
                type="button"
                onClick={() => {
                  setMode("register");
                  setError("");
                }}
                disabled={loading}
                className={`rounded px-3 py-2 text-sm font-semibold transition-colors ${
                  isRegister ? "bg-blue-600 text-white" : "text-gray-400 hover:text-white"
                }`}
              >
                {t("signUp")}
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
            {isRegister && (
              <AuthField
                label={t("name")}
                value={name}
                onChange={(value) => {
                  setName(value);
                  clearFieldError("name");
                }}
                icon={<UserRound size={16} />}
                autoComplete="name"
                placeholder={t("displayName")}
                disabled={loading}
                error={fieldErrors.name}
              />
            )}
            <AuthField
              label={t("email")}
              type="email"
              value={email}
              onChange={(value) => {
                setEmail(value);
                clearFieldError("email");
              }}
              icon={<Mail size={16} />}
              autoComplete="email"
              placeholder="email@example.com"
              disabled={loading}
              error={fieldErrors.email}
            />
            <AuthField
              label={t("password")}
              type="password"
              value={password}
              onChange={(value) => {
                setPassword(value);
                clearFieldError("password");
              }}
              icon={<LockKeyhole size={16} />}
              autoComplete={isRegister ? "new-password" : "current-password"}
              placeholder="********"
              disabled={loading}
              error={fieldErrors.password}
            />
            {isRegister && (
              <>
                <AuthField
                  label={t("confirmPassword")}
                  type="password"
                  value={confirmPw}
                  onChange={(value) => {
                    setConfirmPw(value);
                    clearFieldError("confirmPw");
                  }}
                  icon={<LockKeyhole size={16} />}
                  autoComplete="new-password"
                  placeholder="********"
                  disabled={loading}
                  error={fieldErrors.confirmPw}
                />
                <p className="text-xs leading-5 text-gray-500">
                  {t("passwordRequirementHint")}
                </p>
              </>
            )}

            {error && (
              <div role="alert" className="flex gap-2 rounded border border-red-500/25 bg-red-500/10 px-3 py-2 text-sm leading-5 text-red-100">
                <AlertCircle size={16} className="mt-0.5 flex-shrink-0 text-red-300" />
                <span>{error}</span>
              </div>
            )}

            {success && (
              <div role="status" className="flex gap-2 rounded border border-emerald-500/25 bg-emerald-500/10 px-3 py-2 text-sm leading-5 text-emerald-100">
                <CheckCircle2 size={16} className="mt-0.5 flex-shrink-0 text-emerald-300" />
                <span>{success}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="flex min-h-10 w-full items-center justify-center gap-2 rounded bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-blue-500 disabled:cursor-wait disabled:bg-blue-800"
            >
              {loading && <Loader2 size={16} className="animate-spin" />}
              {loading ? (isRegister ? t("creatingAccount") : t("signingIn")) : (isRegister ? t("createAccount") : t("signIn"))}
            </button>
            </form>

            <p className="mt-5 text-center text-sm text-gray-400">
              {isRegister ? t("hasAccount") : t("noAccount")}{" "}
              <button
                type="button"
                onClick={switchMode}
                className="font-semibold text-blue-300 hover:text-blue-200 disabled:cursor-wait disabled:opacity-60"
                disabled={loading}
              >
                {isRegister ? t("signIn") : t("signUp")}
              </button>
            </p>
          </div>
        </section>
      </div>
    </div>
  );
};

function AuthBenefit({ text }: { text: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="h-1.5 w-1.5 rounded-full bg-blue-400" />
      <span>{text}</span>
    </div>
  );
}

function AuthField({
  label,
  value,
  onChange,
  icon,
  type = "text",
  placeholder,
  autoComplete,
  disabled,
  error,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  icon: React.ReactNode;
  type?: string;
  placeholder?: string;
  autoComplete?: string;
  disabled?: boolean;
  error?: string;
}) {
  const inputId = React.useId();
  const errorId = `${inputId}-error`;

  return (
    <div>
      <label htmlFor={inputId} className="block text-xs font-medium text-gray-400">
        {label}
      </label>
      <div className="mt-1 flex items-center gap-2 rounded border border-gray-700 bg-gray-900 px-3 py-2 transition-colors focus-within:border-blue-500">
        <span className="text-gray-500">{icon}</span>
        <input
          id={inputId}
          type={type}
          required
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="min-w-0 flex-1 bg-transparent text-sm text-white outline-none placeholder:text-gray-600 disabled:cursor-wait"
          placeholder={placeholder}
          autoComplete={autoComplete}
          disabled={disabled}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? errorId : undefined}
        />
      </div>
      {error && (
        <p id={errorId} className="mt-1 text-xs leading-5 text-red-300">
          {error}
        </p>
      )}
    </div>
  );
}

function validateAuthForm({
  isRegister,
  name,
  email,
  password,
  confirmPw,
  t,
}: {
  isRegister: boolean;
  name: string;
  email: string;
  password: string;
  confirmPw: string;
  t: (key: TranslationKey) => string;
}): AuthFieldErrors {
  const errors: AuthFieldErrors = {};
  const normalizedEmail = email.trim();

  if (isRegister && !name.trim()) {
    errors.name = t("nameRequired");
  }
  if (!normalizedEmail) {
    errors.email = t("emailRequired");
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail)) {
    errors.email = t("invalidEmail");
  }
  if (!password) {
    errors.password = t("passwordRequired");
  } else if (isRegister && password.length < 6) {
    errors.password = t("passwordMinLength");
  }
  if (isRegister && !confirmPw) {
    errors.confirmPw = t("confirmPasswordRequired");
  } else if (isRegister && password !== confirmPw) {
    errors.confirmPw = t("passwordsMismatch");
  }

  return errors;
}

function formatAuthError(
  error: string | undefined,
  t: (key: TranslationKey) => string,
): string {
  if (!error) return t("somethingWentWrong");
  if (/^\[[A-Z]+_[A-Z0-9]+\]\s+/.test(error)) return error;
  const authErrorKeys: TranslationKey[] = [
    "invalidCredentials",
    "emailExists",
    "passwordsMismatch",
    "passwordMinLength",
    "nameRequired",
    "emailRequired",
    "invalidEmail",
    "passwordRequired",
    "confirmPasswordRequired",
    "checkFormFields",
  ];
  return authErrorKeys.includes(error as TranslationKey)
    ? t(error as TranslationKey)
    : t("authGenericError");
}

export default AuthModal;
