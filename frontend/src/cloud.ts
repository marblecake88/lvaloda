// Thin wrapper around tg.CloudStorage with a localStorage fallback for dev.
// Used to persist the "active session" so you can resume where you left off
// after closing the Mini App.

import { tg } from "./tg";

const LS_FALLBACK = "lvaloda_active_session";

export interface ActiveSession {
  mode: "dialog" | "exam" | "picture" | "shadowing" | "reading";
  sessionId: number;
  scenario: string;
  /** Where to send the user back to */
  route: string;
  /** Unix ms — stale entries (>12h) are ignored */
  savedAt: number;
}

async function cloudSet(key: string, value: string): Promise<void> {
  const storage = tg?.CloudStorage;
  if (!storage) {
    try {
      localStorage.setItem(key, value);
    } catch {}
    return;
  }
  return new Promise((resolve) => {
    storage.setItem(key, value, () => resolve());
  });
}

async function cloudGet(key: string): Promise<string | null> {
  const storage = tg?.CloudStorage;
  if (!storage) {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  }
  return new Promise((resolve) => {
    storage.getItem(key, (_err: unknown, value: string | null | undefined) =>
      resolve(value ?? null)
    );
  });
}

async function cloudRemove(key: string): Promise<void> {
  const storage = tg?.CloudStorage;
  if (!storage) {
    try {
      localStorage.removeItem(key);
    } catch {}
    return;
  }
  return new Promise((resolve) => {
    storage.removeItem(key, () => resolve());
  });
}

export async function saveActive(session: Omit<ActiveSession, "savedAt">): Promise<void> {
  const payload: ActiveSession = { ...session, savedAt: Date.now() };
  try {
    await cloudSet(LS_FALLBACK, JSON.stringify(payload));
  } catch {}
}

export async function loadActive(): Promise<ActiveSession | null> {
  try {
    const raw = await cloudGet(LS_FALLBACK);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as ActiveSession;
    // Stale after 12 hours.
    if (Date.now() - parsed.savedAt > 12 * 60 * 60 * 1000) {
      await cloudRemove(LS_FALLBACK);
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export async function clearActive(): Promise<void> {
  await cloudRemove(LS_FALLBACK);
}
