export const AI_SESSION_SELECTED_EVENT = "lmview:ai-session-selected";

function activeSessionKey(userId: string): string {
  return `lmview_active_ai_session:${userId}`;
}

export function getActiveAiSessionId(userId: string): string | null {
  try {
    return window.localStorage.getItem(activeSessionKey(userId));
  } catch {
    return null;
  }
}

export function setActiveAiSessionId(userId: string, sessionId: string | null): void {
  try {
    if (sessionId) {
      window.localStorage.setItem(activeSessionKey(userId), sessionId);
    } else {
      window.localStorage.removeItem(activeSessionKey(userId));
    }
  } catch {
    // Storage unavailable.
  }
}

export function selectAiSession(userId: string, sessionId: string | null): void {
  setActiveAiSessionId(userId, sessionId);
  window.dispatchEvent(
    new CustomEvent(AI_SESSION_SELECTED_EVENT, {
      detail: { userId, sessionId },
    }),
  );
}
