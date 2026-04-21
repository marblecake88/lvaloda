import { getInitData } from "./tg";

const BASE = ""; // Use Vite proxy in dev; same origin in prod

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "X-Telegram-Init-Data": getInitData(),
    ...((options.headers as Record<string, string>) || {}),
  };
  if (!(options.body instanceof FormData) && options.body) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(BASE + path, { ...options, headers });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return res.json();
}

export interface ScenarioSummary {
  key: string;
  title_lv: string;
  title_ru: string;
}

export interface ScenarioCatalog {
  exam: ScenarioSummary[];
  daily: ScenarioSummary[];
}

export const api = {
  scenarios: () => request<ScenarioCatalog>("/api/scenarios"),

  startChat: (scenario: string) =>
    request<{ session_id: number; reply: string }>("/api/chat/start", {
      method: "POST",
      body: JSON.stringify({ scenario }),
    }),

  sendChat: (session_id: number, text: string) =>
    request<{ reply: string }>("/api/chat/message", {
      method: "POST",
      body: JSON.stringify({ session_id, text }),
    }),

  hint: (text: string) =>
    request<{ hint: string }>("/api/chat/hint", {
      method: "POST",
      body: JSON.stringify({ text }),
    }),

  finishChat: (session_id: number) =>
    request<{
      report: {
        fluency_score: number;
        unnatural_phrases: { said: string; better: string; note_ru: string }[];
        new_vocabulary: string[];
        strengths_ru: string[];
        tips_ru: string[];
        summary_ru: string;
      };
    }>("/api/chat/finish", {
      method: "POST",
      body: JSON.stringify({ session_id }),
    }),

  startExam: (topic: string) =>
    request<{
      session_id: number;
      topic: ScenarioSummary;
      reply: string;
      covered_angles: string[];
    }>("/api/exam/start", {
      method: "POST",
      body: JSON.stringify({ topic }),
    }),

  sendExam: (session_id: number, text: string) =>
    request<{ reply: string }>("/api/exam/message", {
      method: "POST",
      body: JSON.stringify({ session_id, text }),
    }),

  finishExam: (session_id: number) =>
    request<{
      report: {
        covered_angles: string[];
        fluency_score: number;
        unnatural_phrases: { said: string; better: string; note_ru: string }[];
        missed_vocabulary: string[];
        summary_ru: string;
      };
      previously_covered: string[];
    }>("/api/exam/finish", {
      method: "POST",
      body: JSON.stringify({ session_id }),
    }),

  stt: async (blob: Blob, scenario?: string): Promise<string> => {
    const form = new FormData();
    form.append("file", blob, "audio.webm");
    if (scenario) form.append("scenario", scenario);
    const res = await fetch(BASE + "/api/audio/stt", {
      method: "POST",
      headers: { "X-Telegram-Init-Data": getInitData() },
      body: form,
    });
    if (!res.ok) throw new Error(`STT ${res.status}`);
    const data = (await res.json()) as { text: string };
    return data.text;
  },

  ttsUrl: async (text: string, speed: number = 1.0): Promise<string> => {
    const form = new FormData();
    form.append("text", text);
    form.append("speed", String(speed));
    const r = await fetch(BASE + "/api/audio/tts", {
      method: "POST",
      headers: { "X-Telegram-Init-Data": getInitData() },
      body: form,
    });
    if (!r.ok) {
      const body = await r.text().catch(() => "");
      throw new Error(`TTS ${r.status}: ${body.slice(0, 200)}`);
    }
    const blob = await r.blob();
    return URL.createObjectURL(blob);
  },

  // --- Vocabulary ---
  listWords: (topic?: string) =>
    request<
      {
        id: number;
        word_lv: string;
        translation_ru: string;
        example: string | null;
        topic: string | null;
        created_at: string;
      }[]
    >("/api/words" + (topic ? `?topic=${encodeURIComponent(topic)}` : "")),

  addWord: (body: {
    word_lv: string;
    translation_ru: string;
    example?: string;
    topic?: string;
  }) =>
    request<{ id: number }>("/api/words", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  deleteWord: (id: number) =>
    request<{ ok: boolean }>(`/api/words/${id}`, { method: "DELETE" }),

  // --- Errors (auto-collected from Dabiskāk) ---
  listErrors: (topic?: string) =>
    request<
      {
        id: number;
        said: string;
        better: string;
        note_ru: string | null;
        topic: string | null;
        created_at: string;
      }[]
    >("/api/errors" + (topic ? `?topic=${encodeURIComponent(topic)}` : "")),

  deleteError: (id: number) =>
    request<{ ok: boolean }>(`/api/errors/${id}`, { method: "DELETE" }),

  // --- Prep (pre-task planning) ---
  prep: (scenarioKey: string) =>
    request<{
      scenario: { key: string; title_lv: string; title_ru: string };
      chunks: { lv: string; ru: string }[];
      key_words: string[];
      sample_angles: string[];
    }>(`/api/prep/${encodeURIComponent(scenarioKey)}`),

  // --- Reflection ---
  saveReflection: (session_id: number | null, text: string) =>
    request<{ ok: boolean }>("/api/reflection", {
      method: "POST",
      body: JSON.stringify({ session_id, text }),
    }),

  // --- Task repeat ---
  repeatExam: (session_id: number) =>
    request<{
      session_id: number;
      topic: ScenarioSummary;
      reply: string;
      covered_angles: string[];
    }>("/api/exam/repeat", {
      method: "POST",
      body: JSON.stringify({ session_id }),
    }),

  // --- Shadowing ---
  shadowingStart: (topic?: string) =>
    request<{
      session_id: number;
      topic: ScenarioSummary;
      phrases: { lv: string; ru: string }[];
    }>("/api/shadowing/start", {
      method: "POST",
      body: JSON.stringify({ topic: topic || null }),
    }),

  shadowingTtsUrl: (session_id: number, idx: number, speed = 1.0) => {
    return fetch(
      `${BASE}/api/shadowing/${session_id}/tts/${idx}?speed=${speed}`,
      {
        headers: { "X-Telegram-Init-Data": getInitData() },
      }
    ).then(async (r) => {
      if (!r.ok) throw new Error(`TTS ${r.status}`);
      const blob = await r.blob();
      return URL.createObjectURL(blob);
    });
  },

  // --- Top phrases ---
  phraseCategories: () =>
    request<{
      categories: {
        key: string;
        title_lv: string;
        title_ru: string;
        count: number;
        last_run: { known: number; total: number; at: string } | null;
      }[];
    }>("/api/phrases/categories"),

  phrasesIn: (category: string) =>
    request<{
      category: string;
      items: { lv: string; ru: string; hint_ru: string | null }[];
    }>(`/api/phrases/${encodeURIComponent(category)}`),

  phraseRuns: (category: string, limit = 10) =>
    request<{
      runs: {
        id: number;
        total: number;
        known: number;
        duration_sec: number | null;
        created_at: string;
      }[];
    }>(`/api/phrases/${encodeURIComponent(category)}/runs?limit=${limit}`),

  savePhraseRun: (payload: {
    category: string;
    total: number;
    known: number;
    duration_sec?: number;
  }) =>
    request<{ ok: boolean; id: number }>("/api/phrases/run", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  // --- Minimal pairs ---
  minimalPairNext: () =>
    request<{
      a: string;
      b: string;
      a_ru: string;
      b_ru: string;
      note_ru: string;
      correct: "a" | "b";
    }>("/api/minimal-pairs/next"),

  // --- Picture description ---
  pictureScenes: () =>
    request<{
      scenes: { key: string; topic_lv: string; topic_ru: string }[];
    }>("/api/picture/scenes"),

  pictureHistory: (limit = 30) =>
    request<{
      pictures: {
        id: number;
        scene_key: string;
        topic_lv: string;
        topic_ru: string;
        prompt_lv: string;
        image_url: string;
        created_at: string;
      }[];
    }>(`/api/picture/history?limit=${limit}`),

  pictureGenerate: (scene_key: string | null) =>
    request<{
      id: number;
      scene_key: string;
      topic_lv: string;
      topic_ru: string;
      prompt_lv: string;
      image_url: string;
      created_at: string;
    }>("/api/picture/generate", {
      method: "POST",
      body: JSON.stringify({ scene_key }),
    }),

  pictureGet: (id: number) =>
    request<{
      id: number;
      scene_key: string;
      topic_lv: string;
      topic_ru: string;
      prompt_lv: string;
      image_url: string;
      created_at: string;
    }>(`/api/picture/${id}`),

  pictureDelete: (id: number) =>
    request<{ ok: boolean }>(`/api/picture/${id}`, { method: "DELETE" }),

  finishPicture: (session_id: number, picture_id: number) =>
    request<{
      report: {
        what_is_there_lv: string;
        what_is_there_ru: string;
        key_vocabulary: string[];
        user_accuracy_score: number;
        missed_elements_ru: string[];
        unnatural_phrases: { said: string; better: string; note_ru: string }[];
        tips_ru: string[];
        summary_ru: string;
      };
    }>("/api/picture/finish", {
      method: "POST",
      body: JSON.stringify({ session_id, picture_id }),
    }),

  // --- Translator ---
  translateText: (text: string) =>
    request<{ source_lang: string; source_text: string; translation: string }>(
      "/api/translate/text",
      { method: "POST", body: JSON.stringify({ text }) }
    ),

  translateAudio: async (blob: Blob) => {
    const form = new FormData();
    form.append("file", blob, "audio.webm");
    const res = await fetch(BASE + "/api/translate/audio", {
      method: "POST",
      headers: { "X-Telegram-Init-Data": getInitData() },
      body: form,
    });
    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new Error(`${res.status}: ${body.slice(0, 200)}`);
    }
    return (await res.json()) as {
      source_lang: string;
      source_text: string;
      translation: string;
    };
  },

  // --- Stats ---
  statsSummary: () =>
    request<{
      streak: number;
      goal_minutes: number;
      today_minutes: number;
      today_messages: number;
      week_minutes: number;
      week_days_active: number;
      calendar: Record<string, { messages: number; minutes: number }>;
      topic_counts: Record<string, number>;
    }>("/api/stats/summary"),
};
