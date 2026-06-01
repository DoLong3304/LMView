import type { AiMessage } from "@/features/ai/types";
import type { AiMode, LocalAiHelpSession } from "@/types";

function storageKey(userId: string): string {
  return `lmview_ai_help_sessions:${userId}`;
}

function safeParseSessions(raw: string | null): LocalAiHelpSession[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function loadLocalAiSessions(userId: string): LocalAiHelpSession[] {
  try {
    return safeParseSessions(window.localStorage.getItem(storageKey(userId)));
  } catch {
    return [];
  }
}

export function saveLocalAiSessions(
  userId: string,
  sessions: LocalAiHelpSession[],
): void {
  try {
    window.localStorage.setItem(storageKey(userId), JSON.stringify(sessions.slice(0, 25)));
  } catch {
    // Storage unavailable.
  }
}

export function upsertLocalAiSession(params: {
  userId: string;
  sessionId: string | null;
  title: string;
  mode: AiMode;
  messages: AiMessage[];
}): LocalAiHelpSession {
  const sessions = loadLocalAiSessions(params.userId);
  const now = new Date().toISOString();
  const id = params.sessionId || `local-help-${Date.now()}`;
  const existing = sessions.find((session) => session.id === id);
  const nextSession: LocalAiHelpSession = {
    id,
    userId: params.userId,
    title: params.title,
    mode: params.mode,
    messages: params.messages,
    created_at: existing?.created_at || now,
    updated_at: now,
  };
  const nextSessions = [
    nextSession,
    ...sessions.filter((session) => session.id !== id),
  ];
  saveLocalAiSessions(params.userId, nextSessions);
  return nextSession;
}

export function deleteLocalAiSession(userId: string, sessionId: string): void {
  const sessions = loadLocalAiSessions(userId).filter((session) => session.id !== sessionId);
  saveLocalAiSessions(userId, sessions);
}
