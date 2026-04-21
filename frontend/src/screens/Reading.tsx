import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { clearActive, saveActive } from "../cloud";
import InputBar from "../components/InputBar";
import { haptic, notify, showBackButton } from "../tg";

interface Msg {
  role: "user" | "assistant";
  text: string;
}

interface ReadingText {
  id: string;
  title_lv: string;
  topic: string;
  topic_title_lv: string;
  body: string;
  questions: string[];
  source: string | null;
}

interface Report {
  per_question: {
    question: string;
    user_answer_summary: string;
    understanding: "full" | "partial" | "missed";
    correct_answer_lv: string;
    note_ru: string;
  }[];
  understanding_score: number;
  unnatural_phrases: { said: string; better: string; note_ru: string }[];
  missed_vocabulary: string[];
  summary_ru: string;
}

export default function Reading() {
  const { textId } = useParams();
  const navigate = useNavigate();
  const [text, setText] = useState<ReadingText | null>(null);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [awaitingReply, setAwaitingReply] = useState(false);
  const [finishing, setFinishing] = useState(false);
  const [report, setReport] = useState<Report | null>(null);
  const [textExpanded, setTextExpanded] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const messagesRef = useRef<HTMLDivElement>(null);

  const PRESETS = ["Esmu gatavs.", "Lūdzu, atkārtojiet.", "Es tā īsti nezinu."];

  useEffect(() => showBackButton(() => goHome()), [navigate]);

  useEffect(() => {
    if (!textId) return;
    let cancelled = false;
    api.startReading(textId)
      .then((res) => {
        if (cancelled) return;
        setSessionId(res.session_id);
        setText(res.text);
        setMessages([{ role: "assistant", text: res.reply }]);
      })
      .catch((e) => !cancelled && setErr(String(e)));
    return () => {
      cancelled = true;
    };
  }, [textId]);

  useEffect(() => {
    messagesRef.current?.scrollTo({
      top: messagesRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, awaitingReply]);

  async function send(userText: string) {
    if (!sessionId || !text) return;
    setMessages((prev) => [...prev, { role: "user", text: userText }]);
    setAwaitingReply(true);
    try {
      const { reply } = await api.sendReading(sessionId, userText);
      setMessages((prev) => [...prev, { role: "assistant", text: reply }]);
      saveActive({
        mode: "reading",
        sessionId,
        scenario: text.id,
        route: `/reading/${text.id}`,
      });
    } finally {
      setAwaitingReply(false);
    }
  }

  function goHome() {
    clearActive();
    navigate("/reading");
  }

  async function playTts(textToPlay: string, speed: number = 1.0) {
    haptic("soft");
    try {
      const url = await api.ttsUrl(textToPlay, speed);
      new Audio(url).play();
    } catch (e) {
      setErr(String(e));
    }
  }

  async function finish() {
    if (!sessionId) return;
    setFinishing(true);
    haptic("heavy");
    try {
      const { report: r } = await api.finishReading(sessionId);
      setReport(r);
      notify("success");
    } catch (e) {
      setErr(String(e));
      notify("error");
    } finally {
      setFinishing(false);
    }
  }

  if (report && text) {
    return <ReportView text={text} report={report} onBack={() => navigate("/reading")} />;
  }

  return (
    <div className="screen screen--chat">
      <div className="topbar">
        <button className="icon-pill" onClick={goHome}>‹</button>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="topbar-title">📖 {text?.title_lv ?? "…"}</div>
          <div className="topbar-sub">
            Lasīšana · {text?.topic_title_lv?.split("(")[0]?.trim() ?? ""}
          </div>
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

      {err && <div className="toast" onClick={() => setErr(null)}>{err}</div>}

      {text && (
        <div className={`reading-panel${textExpanded ? "" : " reading-panel--collapsed"}`}>
          <div className="reading-panel-head">
            <div className="reading-panel-title">{text.title_lv}</div>
            <div className="reading-panel-actions">
              <button
                className="msg-action"
                onClick={() => playTts(`${text.title_lv}. ${text.body}`)}
                title="Noklausīties"
              >
                🔊
              </button>
              <button
                className="msg-action"
                onClick={() => setTextExpanded((v) => !v)}
                title={textExpanded ? "Sakļaut" : "Izvērst"}
              >
                {textExpanded ? "▲" : "▼"}
              </button>
            </div>
          </div>
          {textExpanded && (
            <div className="reading-panel-body">
              {text.body.split("\n\n").map((p, i) => (
                <p key={i}>{p}</p>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="chat-messages" ref={messagesRef}>
        {messages.map((m, i) => (
          <div key={i} className="chat-group">
            <div className={`msg ${m.role}`}>{m.text}</div>
            {m.role === "assistant" && (
              <div className="msg-actions">
                <button className="msg-action" onClick={() => playTts(m.text)}>🔊</button>
                <button className="msg-action" onClick={() => playTts(m.text, 0.8)}>🐢</button>
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
        scenario={`reading:${text?.id || ""}`}
        placeholder="Atbildiet latviski…"
        disabled={awaitingReply || finishing || !sessionId}
        onSend={send}
      />
    </div>
  );
}

function ReportView({
  text,
  report,
  onBack,
}: {
  text: ReadingText;
  report: Report;
  onBack: () => void;
}) {
  const labelMap: Record<string, string> = {
    full: "✅ Pilns",
    partial: "🟡 Daļējs",
    missed: "❌ Nokavēts",
  };
  return (
    <div className="screen">
      <div className="home-heading">
        <div>
          <div className="title">📖 Atskaite</div>
          <div className="subtitle">{text.title_lv}</div>
        </div>
      </div>

      <div className="streak-card" style={{ textAlign: "center" }}>
        <div className="streak-number">{report.understanding_score}/5</div>
        <div className="streak-label">teksta izpratne</div>
      </div>

      {report.summary_ru && (
        <div className="report-card">
          <div className="report-section-title">Kopsavilkums</div>
          <p style={{ margin: 0, lineHeight: 1.5 }}>{report.summary_ru}</p>
        </div>
      )}

      <div className="report-card">
        <div className="report-section-title">Atbildes uz jautājumiem</div>
        {report.per_question.map((q, i) => (
          <div key={i} className="reading-q">
            <div className="reading-q-head">
              <span className="reading-q-status">
                {labelMap[q.understanding] || q.understanding}
              </span>
              <span className="reading-q-text">{q.question}</span>
            </div>
            {q.user_answer_summary && (
              <div className="reading-q-user">
                Твой ответ: <i>{q.user_answer_summary}</i>
              </div>
            )}
            {q.correct_answer_lv && (
              <div className="reading-q-correct">
                <strong>Paraugs:</strong> {q.correct_answer_lv}
              </div>
            )}
            {q.note_ru && <div className="reading-q-note">{q.note_ru}</div>}
          </div>
        ))}
      </div>

      {report.missed_vocabulary?.length > 0 && (
        <div className="report-card">
          <div className="report-section-title">Ключевая лексика</div>
          <ul style={{ margin: 0, paddingLeft: 18, lineHeight: 1.6 }}>
            {report.missed_vocabulary.map((v, i) => (
              <li key={i}>{v}</li>
            ))}
          </ul>
        </div>
      )}

      {report.unnatural_phrases?.length > 0 && (
        <div className="report-card">
          <div className="report-section-title">Natūralāk</div>
          {report.unnatural_phrases.map((p, i) => (
            <div key={i} style={{ marginBottom: 10 }}>
              <div>• <i>{p.said}</i></div>
              <div>→ <strong>{p.better}</strong></div>
              {p.note_ru && <div style={{ opacity: 0.7, fontSize: 13 }}>{p.note_ru}</div>}
            </div>
          ))}
        </div>
      )}

      <div className="links-row" style={{ marginTop: 16 }}>
        <button className="btn" onClick={onBack}>Citu tekstu</button>
      </div>
    </div>
  );
}
