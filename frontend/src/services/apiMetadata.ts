export interface ApiAvailability<T> {
  available: boolean;
  data: T | null;
  reason?: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function candidateMetadata(payload: unknown): Array<Record<string, unknown>> {
  if (!isRecord(payload)) return [];

  const candidates: Array<Record<string, unknown>> = [payload];
  if (isRecord(payload.metadata)) candidates.push(payload.metadata);
  if (isRecord(payload.data) && isRecord(payload.data.metadata)) {
    candidates.push(payload.data.metadata);
  }

  return candidates;
}

export function isUnavailableApiPayload(payload: unknown): boolean {
  return candidateMetadata(payload).some((meta) => {
    const dataType = String(meta.data_type ?? "").toLowerCase();
    return (
      meta.is_placeholder === true ||
      meta.is_mock === true ||
      meta.is_synthetic === true ||
      dataType === "placeholder" ||
      dataType === "mock"
    );
  });
}

export function normalizeApiPayloadOrUnavailable<T>(
  payload: unknown,
  extractData: (payload: unknown) => T,
): ApiAvailability<T> {
  if (isUnavailableApiPayload(payload)) {
    return {
      available: false,
      data: null,
      reason: "API returned placeholder or mock metadata.",
    };
  }

  return {
    available: true,
    data: extractData(payload),
  };
}
