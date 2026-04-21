import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import InputBar from "../components/InputBar";
import { haptic, notify, showBackButton } from "../tg";

interface Msg {
  role: "user" | "assistant";
  text: string;
}

interface PictureSummary {
  id: number;
  scene_key: string;
  topic_lv: string;
  topic_ru: string;
  prompt_lv: string;
  image_url: string;
  created_at: string;
}

interface Scene {
  key: string;
  topic_lv: string;
  topic_ru: string;
}

interface PictureReport {
  what_is_there_lv: string;
  what_is_there_ru: string;
  key_vocabulary: string[];
  user_accuracy_score: number;
  missed_elements_ru: string[];
  unnatural_phrases: { said: string; better: string; note_ru: string }[];
  tips_ru: string[];
  summary_ru: string;
}

export default function Picture() {
  const navigate = useNavigate();

  const [picture, setPicture] = useState<PictureSummary | null>(null);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [awaiting, setAwaiting] = useState(false);
  const [finishing, setFinishing] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [report, setReport] = useState<PictureReport | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [sheet, setSheet] = useState<"scenes" | "history" | null>(null);
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [history, setHistory] = useState<PictureSummary[]>([]);

  const messagesRef = useRef<HTMLDivElement>(null);

  useEffect(() => showBackButton(() => navigate("/")), [navigate]);

  // On mount: fetch history + scenes; pick most recent picture if any.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [s, h] = await Promise.all([
          api.pictureScenes(),
          api.pictureHistory(),
        ]);
        if (cancelled) return;
        setScenes(s.scenes);
        setHistory(h.pictures);
        if (h.pictures.length > 0) {
          await loadPicture(h.pictures[0]);
        } else {
          // No history → prompt user to pick
          setSheet("scenes");
        }
      } catch (e) {
        if (!cancelled) setErr(String(e));
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    messagesRef.current?.scrollTo({
      top: messagesRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, awaiting]);

  async function loadPicture(p: PictureSummary) {
    setPicture(p);
    setMessages([]);
    setReport(null);
    setSessionId(null);
    try {
      const res = await api.startChat("picture_desc");
      setSessionId(res.session_id);
      setMessages([{ role: "assistant", text: res.reply }]);
    } catch (e) {
      setErr(String(e));
    }
  }

  async function generate(scene_key: string | null) {
    setSheet(null);
    setGenerating(true);
    setPicture(null);
    setMessages([]);
    setReport(null);
    haptic("medium");
    try {
      const p = await api.pictureGenerate(scene_key);
      setHistory((prev) => [p, ...prev]);
      await loadPicture(p);
    } catch (e) {
      setErr(String(e));
    } finally {
      setGenerating(false);
    }
  }

  async function send(text: string) {
    if (!sessionId) return;
    setMessages((prev) => [...prev, { role: "user", text }]);
    setAwaiting(true);
    try {
      const { reply } = await api.sendChat(sessionId, text);
      setMessages((prev) => [...prev, { role: "assistant", text: reply }]);
      haptic("light");
    } finally {
      setAwaiting(false);
    }
  }

  async function finish() {
    if (!sessionId || !picture || finishing) return;
    setFinishing(true);
    haptic("heavy");
    try {
      const { report } = await api.finishPicture(sessionId, picture.id);
      setReport(report);
      notify("success");
    } catch (e) {
      setErr(String(e));
      notify("error");
    } finally {
      setFinishing(false);
    }
  }

  async function playLv(text: string) {
    if (!text.trim()) return;
    haptic("soft");
    try {
      const url = await api.ttsUrl(text);
      new Audio(url).play();
    } catch (e) {
      setErr(String(e));
    }
  }

  async function removeFromHistory(id: number) {
    haptic("soft");
    try {
      await api.pictureDelete(id);
      setHistory((prev) => prev.filter((p) => p.id !== id));
      if (picture?.id === id) setPicture(null);
    } catch (e) {
      setErr(String(e));
    }
  }

  if (report) {
    return (
      <PictureReportView
        picture={picture}
        report={report}
        onPlay={playLv}
        onNew={() => setSheet("scenes")}
        onBack={() => navigate("/")}
      />
    );
  }

  return (
    <div className="screen">
      <div className="topbar">
        <button className="icon-pill" onClick={() => navigate("/")}>‹</button>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="topbar-title">🖼 Apraksti attēlu</div>
          {picture && (
            <div className="topbar-sub">{picture.topic_lv}</div>
          )}
        </div>
        <button
          className="icon-pill"
          onClick={() => setSheet("history")}
          title="История"
          aria-label="История"
        >
          📚
        </button>
        <button
          className="icon-pill"
          onClick={() => setSheet("scenes")}
          title="Новая"
          aria-label="Новая"
        >
          ↻
        </button>
        <button
          className="btn ghost"
          style={{ padding: "8px 12px", fontSize: 13 }}
          onClick={finish}
          disabled={finishing || messages.length < 3}
        >
          {finishing ? "…" : "Beigt"}
        </button>
      </div>

      {err && <div className="toast" onClick={() => setErr(null)}>{err}</div>}

      {picture ? (
        <div className="picture-wrap">
          <img src={picture.image_url} alt="scene" className="picture-img" />
          <div className="picture-prompt">{picture.prompt_lv}</div>
        </div>
      ) : generating ? (
        <div className="picture-wrap picture-skeleton">
          <div className="picture-img picture-skeleton-img">
            <span>🎨 Grok рисует…</span>
          </div>
        </div>
      ) : (
        <div className="picture-wrap" style={{ padding: 24, textAlign: "center" }}>
          <div style={{ fontSize: 32, marginBottom: 8 }}>🖼</div>
          <div style={{ fontSize: 14, color: "var(--text-dim)" }}>
            Нет картинок. Нажми ↻ чтобы сгенерировать новую.
          </div>
        </div>
      )}

      <div className="chat-messages" ref={messagesRef} style={{ maxHeight: 260 }}>
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>{m.text}</div>
        ))}
        {awaiting && <div className="typing"><span /><span /><span /></div>}
      </div>

      <InputBar
        scenario="picture_desc"
        placeholder="Apraksti latviski…"
        disabled={awaiting || finishing || !sessionId}
        onSend={send}
      />

      {sheet === "scenes" && (
        <ScenePicker
          scenes={scenes}
          onClose={() => setSheet(null)}
          onPick={(key) => generate(key)}
          onRandom={() => generate(null)}
          hasHistory={history.length > 0}
          onSwitchToHistory={() => setSheet("history")}
        />
      )}

      {sheet === "history" && (
        <HistorySheet
          items={history}
          onClose={() => setSheet(null)}
          onPick={(p) => {
            setSheet(null);
            loadPicture(p);
          }}
          onDelete={removeFromHistory}
          onNew={() => setSheet("scenes")}
        />
      )}
    </div>
  );
}

function ScenePicker({
  scenes,
  onClose,
  onPick,
  onRandom,
  hasHistory,
  onSwitchToHistory,
}: {
  scenes: Scene[];
  onClose: () => void;
  onPick: (key: string) => void;
  onRandom: () => void;
  hasHistory: boolean;
  onSwitchToHistory: () => void;
}) {
  return (
    <>
      <div className="sheet-backdrop" onClick={onClose} />
      <div className="sheet" style={{ maxHeight: "75vh", overflowY: "auto" }}>
        <div className="sheet-handle" />
        <h3>Новая картинка</h3>

        <button
          className="cta-exam"
          style={{ marginBottom: 14 }}
          onClick={onRandom}
        >
          <div className="cta-exam-title">🎲 Случайная тема</div>
          <div className="cta-exam-sub">Grok сам выберет сцену</div>
        </button>

        <div className="review-label" style={{ marginBottom: 8 }}>
          Или выбери тему:
        </div>

        <div className="scenarios">
          {scenes.map((s) => (
            <button
              key={s.key}
              className="scenario-card"
              onClick={() => onPick(s.key)}
            >
              <div>
                <div className="scenario-title">{s.topic_lv}</div>
                <div className="scenario-sub">{s.topic_ru}</div>
              </div>
              <div className="scenario-arrow">›</div>
            </button>
          ))}
        </div>

        {hasHistory && (
          <button
            className="btn ghost"
            style={{ width: "100%", marginTop: 12 }}
            onClick={onSwitchToHistory}
          >
            📚 Открыть историю
          </button>
        )}
      </div>
    </>
  );
}

function HistorySheet({
  items,
  onClose,
  onPick,
  onDelete,
  onNew,
}: {
  items: PictureSummary[];
  onClose: () => void;
  onPick: (p: PictureSummary) => void;
  onDelete: (id: number) => void;
  onNew: () => void;
}) {
  return (
    <>
      <div className="sheet-backdrop" onClick={onClose} />
      <div className="sheet" style={{ maxHeight: "80vh", overflowY: "auto" }}>
        <div className="sheet-handle" />
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
          <h3 style={{ flex: 1, margin: 0 }}>История картинок</h3>
          <button className="btn" style={{ padding: "6px 12px", fontSize: 13 }} onClick={onNew}>
            ↻ Новая
          </button>
        </div>

        {items.length === 0 ? (
          <div className="empty">История пуста.</div>
        ) : (
          <div className="history-grid">
            {items.map((p) => (
              <div key={p.id} className="history-item">
                <img
                  src={p.image_url}
                  alt={p.topic_lv}
                  className="history-img"
                  onClick={() => onPick(p)}
                />
                <div className="history-caption">
                  <div className="history-title">{p.topic_lv}</div>
                  <button
                    className="icon-pill"
                    onClick={() => onDelete(p.id)}
                    aria-label="Удалить"
                    style={{ width: 24, height: 24, fontSize: 13 }}
                  >
                    ✕
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}

function PictureReportView({
  picture,
  report,
  onPlay,
  onNew,
  onBack,
}: {
  picture: PictureSummary | null;
  report: PictureReport;
  onPlay: (text: string) => void;
  onNew: () => void;
  onBack: () => void;
}) {
  return (
    <div className="screen">
      <div className="topbar">
        <button className="icon-pill" onClick={onBack}>‹</button>
        <div style={{ flex: 1 }}>
          <div className="topbar-title">Разбор</div>
          <div className="topbar-sub">{picture?.topic_lv}</div>
        </div>
      </div>

      {picture && (
        <div className="picture-wrap" style={{ marginBottom: 12 }}>
          <img src={picture.image_url} alt="scene" className="picture-img" />
        </div>
      )}

      <div className="report">
        <div className="report-card">
          <h3>Точность описания</h3>
          <div className="report-score">
            {report.user_accuracy_score}
            <span className="report-score-max">/5</span>
          </div>
        </div>

        {report.what_is_there_lv && (
          <div className="report-card">
            <h3>
              Kas attēlā ir{" "}
              <button
                className="msg-action"
                style={{ marginLeft: 6 }}
                onClick={() => onPlay(report.what_is_there_lv)}
              >
                🔊
              </button>
            </h3>
            <div style={{ fontSize: 15, lineHeight: 1.5, marginBottom: 8, fontWeight: 500 }}>
              {report.what_is_there_lv}
            </div>
            {report.what_is_there_ru && (
              <div style={{ fontSize: 13, color: "var(--text-dim)", lineHeight: 1.45 }}>
                {report.what_is_there_ru}
              </div>
            )}
          </div>
        )}

        {report.key_vocabulary?.length > 0 && (
          <div className="report-card">
            <h3>Ключевые слова</h3>
            <ul style={{ margin: 0, paddingLeft: 18, fontSize: 14, lineHeight: 1.6 }}>
              {report.key_vocabulary.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          </div>
        )}

        {report.missed_elements_ru?.length > 0 && (
          <div className="report-card">
            <h3>Что ты пропустил</h3>
            <ul style={{ margin: 0, paddingLeft: 18, fontSize: 14, lineHeight: 1.5 }}>
              {report.missed_elements_ru.map((m, i) => (
                <li key={i} style={{ marginBottom: 4 }}>{m}</li>
              ))}
            </ul>
          </div>
        )}

        {report.unnatural_phrases?.length > 0 && (
          <div className="report-card">
            <h3>Как лучше было бы сказать</h3>
            {report.unnatural_phrases.map((p, i) => (
              <div key={i} className="phrase-item">
                <div className="phrase-said">«{p.said}»</div>
                <div className="phrase-better">→ {p.better}</div>
                {p.note_ru && <div className="phrase-note">{p.note_ru}</div>}
              </div>
            ))}
          </div>
        )}

        {report.tips_ru?.length > 0 && (
          <div className="report-card">
            <h3>Советы</h3>
            <ul style={{ margin: 0, paddingLeft: 18, fontSize: 14, lineHeight: 1.5 }}>
              {report.tips_ru.map((t, i) => (
                <li key={i} style={{ marginBottom: 4 }}>{t}</li>
              ))}
            </ul>
          </div>
        )}

        {report.summary_ru && (
          <div className="report-card">
            <h3>Итог</h3>
            <div style={{ fontSize: 14, lineHeight: 1.45 }}>{report.summary_ru}</div>
          </div>
        )}

        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn ghost" style={{ flex: 1 }} onClick={onNew}>
            🖼 Новая картинка
          </button>
          <button className="btn" style={{ flex: 1 }} onClick={onBack}>
            На главную
          </button>
        </div>
      </div>
    </div>
  );
}
