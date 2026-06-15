import { describe, expect, it } from "vitest";
import {
  createApiError,
  normalizeError,
  sanitizeTechnicalDetails,
} from "./errors";

describe("role-aware error normalization", () => {
  it("maps market 503 failures to a DATA code with a short user message", () => {
    const error = createApiError("market", 503, {
      detail: "redis-master.internal failed with token=abc123",
      request_id: "req-123",
    }, { endpoint: "http://backend:8080/api/klines?token=abc123" });

    const normalized = normalizeError(error);

    expect(normalized.code).toBe("DATA_503");
    expect(normalized.userMessage).toContain("Market data is temporarily unavailable");
    expect(normalized.endpoint).toBe("/api/klines?token=[redacted]");
    expect(normalized.technicalDetails).not.toContain("abc123");
    expect(normalized.requestId).toBe("req-123");
  });

  it("redacts secrets, URLs, SQL, and local file paths from technical details", () => {
    const sanitized = sanitizeTechnicalDetails(
      "Bearer abc.def token=secret password=hunter2 api_key=supersecret SELECT * FROM users C:\\app\\secret.ts http://postgres:5432/private",
    );

    expect(sanitized).not.toContain("abc.def");
    expect(sanitized).not.toContain("hunter2");
    expect(sanitized).not.toContain("supersecret");
    expect(sanitized).not.toContain("postgres:5432");
    expect(sanitized).not.toContain("C:\\app\\secret.ts");
    expect(sanitized).not.toMatch(/SELECT \*/i);
  });

  it("uses AUTH_401 for authentication errors", () => {
    const error = createApiError("auth", 401, { detail: "invalid credentials" });
    const normalized = normalizeError(error);

    expect(normalized.code).toBe("AUTH_401");
    expect(normalized.userMessage).toContain("We could not sign you in");
  });
});
