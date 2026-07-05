// Centralized role-aware error handling utilities.

export type ErrorArea =
  | "auth"
  | "settings"
  | "market"
  | "chart"
  | "ai"
  | "network"
  | "validation"
  | "general";

export type ErrorCodePrefix =
  | "AUTH"
  | "SETTINGS"
  | "DATA"
  | "CHART"
  | "AI"
  | "NETWORK"
  | "VALIDATION"
  | "UNKNOWN";

export interface NormalizedError {
  code: string;
  userMessage: string;
  adminMessage: string;
  status?: number;
  area: ErrorArea;
  requestId?: string;
  endpoint?: string;
  timestamp: string;
  recoverable: boolean;
  retryable: boolean;
  technicalDetails: string;
  originalType?: string;
}

interface NormalizeErrorOptions {
  area?: ErrorArea;
  status?: number;
  fallbackCode?: string;
  fallbackMessage?: string;
  endpoint?: string;
  requestId?: string;
  technicalDetails?: string;
}

type ApiErrorContext = Exclude<ErrorArea, "chart" | "network" | "validation">;

const GENERIC_USER_ERROR = "We could not complete that request. Please try again.";
const GENERIC_NETWORK_ERROR = "Connection issue. Please check your network and try again.";
const GENERIC_AUTH_ERROR = "We could not sign you in. Please check your account information and try again.";
const GENERIC_PERMISSION_ERROR = "You do not have permission to do that.";
const SECRET_PATTERNS: RegExp[] = [
  /Bearer\s+[A-Za-z0-9._~+/=-]+/gi,
  /(session[_-]?token["']?\s*[:=]\s*["']?)[^"',\s}]+/gi,
  /(password["']?\s*[:=]\s*["']?)[^"',\s}]+/gi,
  /(api[_-]?key["']?\s*[:=]\s*["']?)[^"',\s}]+/gi,
  /(token["']?\s*[:=]\s*["']?)[^"',\s}]+/gi,
  /(secret["']?\s*[:=]\s*["']?)[^"',\s}]+/gi,
  /(authorization["']?\s*[:=]\s*["']?)[^"',\s}]+/gi,
  /postgres(?:ql)?:\/\/[^\s"')]+/gi,
  /https?:\/\/(?:localhost|127\.0\.0\.1|[a-z0-9-]+(?:\.[a-z0-9-]+)*)(?::\d+)?[^\s"')}]*/gi,
  /\b[A-Za-z]:\\[^\n\r\t"'<>]+/g,
  /\/(?:app|workspace|usr|var|etc|home)\/[^\n\r\t"'<>]+/g,
  /\b(?:SELECT|INSERT|UPDATE|DELETE|ALTER|DROP)\s+[\s\S]{0,180}/gi,
];

/** Base application error with categorization. */
export class AppError extends Error {
  public readonly code: string;
  public readonly isRetryable: boolean;
  public readonly originalError?: unknown;
  public readonly status?: number;
  public readonly userMessage: string;
  public readonly adminMessage: string;
  public readonly normalized: NormalizedError;

  constructor(
    message: string,
    code: string = "UNKNOWN_001",
    isRetryable: boolean = false,
    originalError?: unknown,
    options: {
      status?: number;
      userMessage?: string;
      adminMessage?: string;
      area?: ErrorArea;
      endpoint?: string;
      requestId?: string;
      technicalDetails?: string;
    } = {},
  ) {
    super(message);
    this.name = "AppError";
    this.code = normalizeCode(code, options.area, options.status);
    this.isRetryable = isRetryable;
    this.originalError = originalError;
    this.status = options.status;
    this.normalized = normalizeError(originalError ?? message, {
      area: options.area,
      status: options.status,
      fallbackCode: this.code,
      fallbackMessage: options.userMessage,
      endpoint: options.endpoint,
      requestId: options.requestId,
      technicalDetails: options.technicalDetails ?? options.adminMessage ?? message,
    });
    this.userMessage = this.normalized.userMessage;
    this.adminMessage = this.normalized.adminMessage;
  }
}

/** Network/API fetch errors. */
export class NetworkError extends AppError {
  constructor(message: string, status?: number, originalError?: unknown) {
    super(message, status ? `NETWORK_${status}` : "NETWORK_001", true, originalError, {
      status,
      area: "network",
      userMessage: status ? userMessageForStatus(status, "general") : GENERIC_NETWORK_ERROR,
      adminMessage: status ? `HTTP ${status}: ${message}` : message,
    });
    this.name = "NetworkError";
  }
}

/** WebSocket connection/message errors. */
export class WebSocketError extends AppError {
  constructor(message: string, originalError?: unknown) {
    super(message, "NETWORK_002", true, originalError, {
      area: "network",
      userMessage: "Live updates are disconnected. Reconnecting...",
    });
    this.name = "WebSocketError";
  }
}

/** Data validation/parsing errors. */
export class ValidationError extends AppError {
  constructor(message: string, originalError?: unknown) {
    super(message, "VALIDATION_422", false, originalError, {
      area: "validation",
      userMessage: "Please check the highlighted fields and try again.",
    });
    this.name = "ValidationError";
  }
}

/** Authentication errors. */
export class AuthError extends AppError {
  constructor(message: string, originalError?: unknown) {
    super(message, "AUTH_401", false, originalError, {
      area: "auth",
      userMessage: GENERIC_AUTH_ERROR,
    });
    this.name = "AuthError";
  }
}

export function createApiError(
  context: ApiErrorContext,
  status: number,
  payload: unknown,
  options: { endpoint?: string; requestId?: string } = {},
): AppError {
  const area = context === "market" ? "market" : context;
  const detail = extractApiDetail(payload);
  const requestId = options.requestId || extractRequestId(payload);
  const adminMessage = `${context.toUpperCase()} API ${status}${detail ? `: ${detail}` : ""}`;

  return new AppError(adminMessage, codeForStatus(status, area), isRetryableStatus(status), payload, {
    status,
    area,
    userMessage: userMessageForStatus(status, area),
    adminMessage,
    endpoint: options.endpoint,
    requestId,
    technicalDetails: detail || adminMessage,
  });
}

/**
 * Normalize any thrown value into a role-aware safe error object.
 */
export function normalizeError(error: unknown, options: NormalizeErrorOptions = {}): NormalizedError {
  if (error instanceof AppError) {
    return mergeNormalized(error.normalized, options);
  }

  const status = options.status ?? extractStatus(error);
  const area = options.area ?? inferArea(error, status);
  const code = normalizeCode(options.fallbackCode, area, status);
  const requestId = options.requestId ?? extractRequestId(error);
  const rawMessage = extractErrorMessage(error);
  const technicalDetails = sanitizeTechnicalDetails(
    options.technicalDetails || rawMessage || options.fallbackMessage || GENERIC_USER_ERROR,
  );
  const userMessage = options.fallbackMessage || userMessageForCode(code, status, area);
  const adminMessage = buildAdminSummary({
    code,
    status,
    area,
    endpoint: options.endpoint,
    requestId,
    technicalDetails,
  });

  return {
    code,
    userMessage,
    adminMessage,
    status,
    area,
    requestId,
    endpoint: sanitizeEndpoint(options.endpoint),
    timestamp: new Date().toISOString(),
    recoverable: isRecoverableStatus(status),
    retryable: isRetryableStatus(status) || area === "network",
    technicalDetails,
    originalType: getOriginalType(error),
  };
}

/**
 * Normalize any thrown value into a typed AppError.
 * Use in catch blocks to get consistent error objects.
 */
export function categorizeError(error: unknown, options: NormalizeErrorOptions = {}): AppError {
  if (error instanceof AppError) return error;
  const normalized = normalizeError(error, options);
  return new AppError(normalized.technicalDetails, normalized.code, normalized.retryable, error, {
    status: normalized.status,
    area: normalized.area,
    userMessage: normalized.userMessage,
    adminMessage: normalized.adminMessage,
    endpoint: normalized.endpoint,
    requestId: normalized.requestId,
    technicalDetails: normalized.technicalDetails,
  });
}

export function getRoleAwareErrorMessage(
  error: unknown,
  options: {
    isAdmin?: boolean;
    fallback?: string;
    area?: ErrorArea;
    endpoint?: string;
  } = {},
): string {
  const normalized = normalizeError(error, {
    area: options.area,
    endpoint: options.endpoint,
    fallbackMessage: options.fallback,
  });
  if (options.isAdmin) return normalized.adminMessage;
  return `[${normalized.code}] ${normalized.userMessage}`;
}

export function formatNormalizedError(error: NormalizedError, isAdmin: boolean): string {
  return isAdmin ? error.adminMessage : `[${error.code}] ${error.userMessage}`;
}

export function sanitizeTechnicalDetails(value: unknown): string {
  let message = typeof value === "string" ? value : safeStringify(value);
  for (const pattern of SECRET_PATTERNS) {
    message = message.replace(pattern, (_match, prefix?: string) => prefix ? `${prefix}[redacted]` : "[redacted]");
  }
  return message
    .replace(/\b(mock_mode|api_mode|migration phase|schema phase|provider_metadata)\b/gi, "[internal]")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 900);
}

function mergeNormalized(base: NormalizedError, options: NormalizeErrorOptions): NormalizedError {
  const status = options.status ?? base.status;
  const area = options.area ?? base.area;
  const code = normalizeCode(options.fallbackCode ?? base.code, area, status);
  const technicalDetails = sanitizeTechnicalDetails(options.technicalDetails ?? base.technicalDetails);
  return {
    ...base,
    code,
    status,
    area,
    endpoint: sanitizeEndpoint(options.endpoint ?? base.endpoint),
    requestId: options.requestId ?? base.requestId,
    userMessage: options.fallbackMessage ?? base.userMessage,
    adminMessage: buildAdminSummary({
      code,
      status,
      area,
      endpoint: options.endpoint ?? base.endpoint,
      requestId: options.requestId ?? base.requestId,
      technicalDetails,
    }),
    technicalDetails,
  };
}

function normalizeCode(code: string | undefined, area: ErrorArea = "general", status?: number): string {
  if (code && /^[A-Z]+_[A-Z0-9]+$/.test(code)) return code;
  if (code && /^[A-Z]+_\d+$/.test(code)) return code;
  return codeForStatus(status, area);
}

function codeForStatus(status: number | undefined, area: ErrorArea): string {
  const prefix = prefixForArea(area);
  if (!status) return `${prefix}_001`;
  if (status === 401) return "AUTH_401";
  if (status === 403) return `${prefix}_403`;
  if (status === 404) return `${prefix}_404`;
  if (status === 409) return `${prefix}_409`;
  if (status === 422 || status === 400) return area === "chart" ? "CHART_422" : "VALIDATION_422";
  if (status === 429) return `${prefix}_429`;
  if (status >= 500) return `${prefix}_503`;
  return `${prefix}_${status}`;
}

function prefixForArea(area: ErrorArea): ErrorCodePrefix {
  if (area === "auth") return "AUTH";
  if (area === "settings") return "SETTINGS";
  if (area === "market") return "DATA";
  if (area === "chart") return "CHART";
  if (area === "ai") return "AI";
  if (area === "network") return "NETWORK";
  if (area === "validation") return "VALIDATION";
  return "UNKNOWN";
}

function userMessageForCode(code: string, status: number | undefined, area: ErrorArea): string {
  if (area === "auth" || code.startsWith("AUTH_")) return GENERIC_AUTH_ERROR;
  if (area === "market") return status && status >= 500
    ? "Market data is temporarily unavailable. Please try again later."
    : "Market data could not be loaded. Please try again.";
  if (area === "chart") return "The chart could not load this data.";
  if (area === "ai") return "AI Helper could not complete that request. Please try again.";
  if (area === "settings") return "Settings could not be loaded or saved. Please try again.";
  if (area === "network") return GENERIC_NETWORK_ERROR;
  if (area === "validation") return "Please check your input and try again.";
  return GENERIC_USER_ERROR;
}

function userMessageForStatus(status: number | undefined, area: ErrorArea = "general"): string {
  if (!status) return area === "network" ? GENERIC_NETWORK_ERROR : userMessageForCode(`${prefixForArea(area)}_001`, status, area);
  if (status === 400 || status === 422) return "Please check your input and try again.";
  if (status === 401) return GENERIC_AUTH_ERROR;
  if (status === 403) return GENERIC_PERMISSION_ERROR;
  if (status === 404) return "That item could not be found.";
  if (status === 409) return area === "auth"
    ? "An account with those details already exists."
    : "This change conflicts with the latest saved data.";
  if (status === 429) return "Too many requests. Please wait a moment.";
  if (status >= 500) return userMessageForCode(codeForStatus(status, area), status, area);
  return GENERIC_USER_ERROR;
}

function buildAdminSummary(params: {
  code: string;
  status?: number;
  area: ErrorArea;
  endpoint?: string;
  requestId?: string;
  technicalDetails: string;
}): string {
  return [
    `Code: ${params.code}`,
    params.status ? `Status: ${params.status}` : "",
    `Area: ${params.area}`,
    params.endpoint ? `Endpoint: ${sanitizeEndpoint(params.endpoint)}` : "",
    params.requestId ? `Request ID: ${sanitizeTechnicalDetails(params.requestId)}` : "",
    `Time: ${new Date().toISOString()}`,
    params.technicalDetails ? `Technical details: ${params.technicalDetails}` : "",
  ].filter(Boolean).join("\n");
}

function extractApiDetail(payload: unknown): string {
  if (!payload || typeof payload !== "object") return "";
  const detail = (payload as { detail?: unknown; message?: unknown; error?: unknown }).detail
    ?? (payload as { message?: unknown }).message
    ?? (payload as { error?: unknown }).error;
  if (typeof detail === "string") return sanitizeTechnicalDetails(detail);
  if (Array.isArray(detail)) {
    return sanitizeTechnicalDetails(
      detail
        .map((item) => {
          if (typeof item === "string") return item;
          if (item && typeof item === "object") {
            const msg = (item as { msg?: unknown; message?: unknown }).msg;
            const message = (item as { msg?: unknown; message?: unknown }).message;
            return typeof msg === "string" ? msg : typeof message === "string" ? message : "";
          }
          return "";
        })
        .filter(Boolean)
        .join(". "),
    );
  }
  if (detail && typeof detail === "object") return sanitizeTechnicalDetails(detail);
  return "";
}

function extractStatus(error: unknown): number | undefined {
  if (error && typeof error === "object" && "status" in error) {
    const status = (error as { status?: unknown }).status;
    return typeof status === "number" ? status : undefined;
  }
  if (error instanceof Error) {
    const match = error.message.match(/\b(?:HTTP|API error)\s+(\d{3})\b/i);
    return match ? Number(match[1]) : undefined;
  }
  return undefined;
}

function extractRequestId(value: unknown): string | undefined {
  if (!value || typeof value !== "object") return undefined;
  const requestId = (value as { request_id?: unknown; requestId?: unknown; trace_id?: unknown }).request_id
    ?? (value as { requestId?: unknown }).requestId
    ?? (value as { trace_id?: unknown }).trace_id;
  return typeof requestId === "string" ? sanitizeTechnicalDetails(requestId) : undefined;
}

function extractErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (typeof error === "string") return error;
  return safeStringify(error);
}

function inferArea(error: unknown, status?: number): ErrorArea {
  if (error instanceof TypeError && /fetch|network|failed/i.test(error.message)) return "network";
  if (status === 401 || status === 403) return "auth";
  return "general";
}

function isRetryableStatus(status?: number): boolean {
  return !status || status === 408 || status === 429 || status >= 500;
}

function isRecoverableStatus(status?: number): boolean {
  return !status || status >= 400;
}

function sanitizeEndpoint(endpoint?: string): string | undefined {
  if (!endpoint) return undefined;
  return endpoint
    .replace(/^https?:\/\/[^/]+/i, "")
    .replace(/([?&](?:token|session|api_key|password|secret)=)[^&]+/gi, "$1[redacted]")
    .slice(0, 180);
}

function getOriginalType(error: unknown): string | undefined {
  if (error instanceof Error) return error.name;
  if (error === null) return "null";
  return typeof error;
}

function safeStringify(value: unknown): string {
  try {
    return typeof value === "string" ? value : JSON.stringify(value);
  } catch {
    return String(value);
  }
}
