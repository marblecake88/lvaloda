import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, ScenarioSummary } from "../api";
import { clearActive, saveActive } from "../cloud";
import InputBar from "../components/InputBar";
import SaveWordSheet from "../components/SaveWordSheet";
import { haptic, notify, showBackButton } from "../tg";

interface Msg {
  role: "user" | "assistant";
  text: string;
}

interface Report {
  covered_angles: string[];
  fluency_score: number;
  unnatural_phrases: { said: string; better: string; note_ru: string }[];
  missed_vocabulary: string[];
  summary_ru: string;
}

export default function Exam() {
  const { topicKey } = useParams();
  const navigate = useNavigate();
  const [topic, setTopic] = useState<ScenarioSummary | null>(null);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [awaitingReply, setAwaitingReply] = useState(false);
  const [finishing, setFinishing] = useState(false);
  const [report, setReport] = useState<Report | null>(null);
  const [prevCovered, setPrevCovered] = useState<string[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [saveSheet, setSaveSheet] = useState<{ word: string; example: string } | null>(null);
  const messagesRef = useRef<HTMLDivElement>(null);

  const PRESETS = [
    "Lūdzu, atkārtojiet.",
    "Sakiet citiem vārdiem, lūdzu.",
    "Es tā īsti nezinu, bet mēģināšu.",
  ];

  useEffect(() => showBackButton(() => goHome()), [navigate]);

  useEffect(() => {
    if (!topicKey) return;
    let cancelled = false;

    api.startExam(topicKey)
      .then((res) => {
        if (cancelled) return;
        setSessionId(res.session_id);
        setTopic(res.topic);
        setPrevCovered(res.covered_angles);
        setMessages([{ role: "assistant", text: res.reply }]);
      })
      .catch((e) => {
        if (!cancelled) setErr(String(e));
      });

    return () => {
      cancelled = true;
    };
  }, [topicKey]);

  useEffect(() => {
    messagesRef.current?.scrollTo({
      top: messagesRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, awaitingReply]);

  async function send(text: string) {
    if (!sessionId || !topicKey) return;
    setMessages((prev) => [...prev, { role: "user", text }]);
    setAwaitingReply(true);
    try {
      const { reply } = await api.sendExam(sessionId, text);
      setMessages((prev) => [...prev, { role: "assistant", text: reply }]);
      saveActive({
        mode: "exam",
        sessionId,
        scenario: topicKey,
        route: `/exam/${topicKey}`,
      });
    } finally {
      setAwaitingReply(false);
    }
  }

  function goHome() {
    clearActive();
    navigate("/");
  }

  async function playTts(text: string, speed: number = 1.0) {
    haptic("soft");
    try {
      const url = await api.ttsUrl(text, speed);
      new Audio(url).play();
    } catch (e) {
      setErr(String(e));
    }
  }

  function openSave(text: string) {
    haptic("soft");
    setSaveSheet({ word: firstWord(text), example: text.slice(0, 200) });
  }

  const [showReflection, setShowReflection] = useState(false);

  async function finish() {
    if (!sessionId) return;
    setFinishing(true);
    haptic("heavy");
    try {
      const { report } = await api.finishExam(sessionId);
      setReport(report);
      setShowReflection(true);
      notify("success");
    } catch (e) {
      setErr(String(e));
      notify("error");
    } finally {
      setFinishing(false);
    }
  }

  async function repeat() {
    if (!sessionId) return;
    try {
      const res = await api.repeatExam(sessionId);
      setSessionId(res.session_id);
      setMessages([{ role: "assistant", text: res.reply }]);
      setReport(null);
      setShowReflection(false);
      setPrevCovered(res.covered_angles);
    } catch (e) {
      setErr(String(e));
    }
  }

  if (report) {
    return (
      <ReportView
        topic={topic}
        report={report}
        showReflection={showReflection}
        sessionId={sessionId}
        onDoneReflection={() => setShowReflection(false)}
        onBack={() => navigate("/")}
        onRepeat={repeat}
      />
    );
  }

  return (
    <div className="screen screen--chat">
      <div className="topbar">
        <button className="icon-pill" onClick={goHome}>‹</button>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="topbar-title">🎓 {topic?.title_lv ?? "…"}</div>
          <div className="topbar-sub">Eksāmena simulācija · {topic?.title_ru}</div>
        </div>
        <button
          className="btn ghost"
          style={{ padding: "8px 12px", fontSize: 13 }}
          onClick={finish}
          disabled={finishing || messages.length < 2}
        >
          {finishing ? "…" : "Beigt"}
        </button>
      </div>

      {prevCovered.length > 0 && (
        <div className="chips">
          <span className="chip-label">Покрыто:</span>
          {prevCovered.slice(0, 6).map((a) => (
            <span key={a} className="chip">{a}</span>
          ))}
          {prevCovered.length > 6 && (
            <span className="chip">+{prevCovered.length - 6}</span>
          )}
        </div>
      )}

      {err && <div className="toast" onClick={() => setErr(null)}>{err}</div>}

      <div className="chat-messages" ref={messagesRef}>
        {messages.map((m, i) => (
          <div key={i} className="chat-group">
            <div className={`msg ${m.role}`}>{m.text}</div>
            {m.role === "assistant" && (
              <div className="msg-actions">
                <button className="msg-action" onClick={() => playTts(m.text)}>🔊</button>
                <button className="msg-action" onClick={() => playTts(m.text, 0.8)}>🐢</button>
                <button className="msg-action" onClick={() => openSave(m.text)}>🔖</button>
              </div>
            )}
          </div>
        ))}
        {awaitingReply && <div className="typing"><span /><span /><span /></div>}
      </div>

      <div className="presets">
        {PRESETS.map((p) => (
          <button
            key={p}
            className="preset-chip"
            disabled={awaitingReply || finishing || !sessionId}
            onClick={() => send(p)}
          >
            {p}
          </button>
        ))}
      </div>

      <InputBar
        scenario={topicKey || ""}
        placeholder="Atbildiet latviski…"
        disabled={awaitingReply || finishing || !sessionId}
        onSend={send}
      />

      {saveSheet && (
        <SaveWordSheet
          initialWord={saveSheet.word}
          initialExample={saveSheet.example}
          topic={topicKey}
          onClose={() => setSaveSheet(null)}
        />
      )}
    </div>
  );
}

function firstWord(s: string): string {
  const cleaned = s.replace(/[.,!?;:«»"']/g, " ");
  const token = cleaned.split(/\s+/).find((t) => t.length > 2);
  return token || "";
}

function ReportView({
  topic,
  report,
  showReflection,
  sessionId,
  onDoneReflection,
  onBack,
  onRepeat,
}: {
  topic: ScenarioSummary | null;
  report: Report;
  showReflection: boolean;
  sessionId: number | null;
  onDoneReflection: () => void;
  onBack: () => void;
  onRepeat: () => void;
}) {
  const [reflection, setReflection] = useState("");
  const [savingR, setSavingR] = useState(false);

  async function saveReflection() {
    if (!reflection.trim()) {
      onDoneReflection();
      return;
    }
    setSavingR(true);
    try {
      await api.saveReflection(sessionId, reflection.trim());
      notify("success");
    } catch {}
    setSavingR(false);
    onDoneReflection();
  }

  return (
    <div className="screen">
      <div className="topbar">
        <button className="icon-pill" onClick={onBack}>‹</button>
        <div style={{ flex: 1 }}>
          <div className="topbar-title">Разбор</div>
          <div className="topbar-sub">{topic?.title_lv}</div>
        </div>
      </div>

      <div className="report">
        <div className="report-card">
          <h3>Беглость</h3>
          <div className="report-score">
            {report.fluency_score}
            <span className="report-score-max">/5</span>
          </div>
        </div>

        {showReflection && (
          <div className="report-card">
            <h3>30 секунд рефлексии</h3>
            <div style={{ fontSize: 13, color: "var(--text-dim)", marginBottom: 8 }}>
              Одной фразой: что полезного вынес из этой сессии?
            </div>
            <textarea
              className="text-input"
              style={{ width: "100%", minHeight: 80, padding: 12 }}
              value={reflection}
              onChange={(e) => setReflection(e.target.value)}
              placeholder="Новое слово, формулировка, над чем ещё работать…"
            />
            <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
              <button
                className="btn ghost"
                style={{ flex: 1 }}
                onClick={onDoneReflection}
                disabled={savingR}
              >
                Пропустить
              </button>
              <button
                className="btn"
                style={{ flex: 1 }}
                onClick={saveReflection}
                disabled={savingR}
              >
                {savingR ? "…" : "Сохранить"}
              </button>
            </div>
          </div>
        )}

        {report.summary_ru && (
          <div className="report-card">
            <h3>Итог</h3>
            <div>{report.summary_ru}</div>
          </div>
        )}

        {report.unnatural_phrases?.length > 0 && (
          <div className="report-card">
            <h3>Как лучше было бы</h3>
            {report.unnatural_phrases.map((p, i) => (
              <div key={i} className="phrase-item">
                <div className="phrase-said">«{p.said}»</div>
                <div className="phrase-better">→ {p.better}</div>
                {p.note_ru && <div className="phrase-note">{p.note_ru}</div>}
              </div>
            ))}
          </div>
        )}

        {report.missed_vocabulary?.length > 0 && (
          <div className="report-card">
            <h3>Лексика, которую стоит знать</h3>
            <ul style={{ margin: 0, paddingLeft: 18 }}>
              {report.missed_vocabulary.map((w, i) => (
                <li key={i} style={{ marginBottom: 6, fontSize: 14 }}>{w}</li>
              ))}
            </ul>
          </div>
        )}

        {report.covered_angles?.length > 0 && (
          <div className="report-card">
            <h3>Углы, которые сегодня разобрали</h3>
            <div className="chips">
              {report.covered_angles.map((a) => (
                <span key={a} className="chip">{a}</span>
              ))}
            </div>
          </div>
        )}

        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn ghost" style={{ flex: 1 }} onClick={onRepeat}>
            🔁 Повторить ту же тему
          </button>
          <button className="btn" style={{ flex: 1 }} onClick={onBack}>Готово</button>
        </div>
      </div>
    </div>
  );
}
