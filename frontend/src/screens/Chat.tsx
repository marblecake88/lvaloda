import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { saveActive, clearActive } from "../cloud";
import InputBar from "../components/InputBar";
import SaveWordSheet from "../components/SaveWordSheet";
import { haptic, showBackButton } from "../tg";

interface Msg {
  role: "user" | "assistant";
  text: string;
  hint?: string;
}

interface Report {
  fluency_score: number;
  unnatural_phrases: { said: string; better: string; note_ru: string }[];
  new_vocabulary: string[];
  strengths_ru: string[];
  tips_ru: string[];
  summary_ru: string;
}

interface Props {
  mode: "dialog";
}

export default function Chat(_: Props) {
  const { scenarioKey } = useParams();
  const navigate = useNavigate();
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [awaitingReply, setAwaitingReply] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [titleLv, setTitleLv] = useState<string>("");
  const [saveSheet, setSaveSheet] = useState<{ word: string; example: string } | null>(null);
  const [finishing, setFinishing] = useState(false);
  const [report, setReport] = useState<Report | null>(null);
  const [busyAction, setBusyAction] = useState<string | null>(null); // `${idx}:${action}`
  const messagesRef = useRef<HTMLDivElement>(null);

  const isBusy = (idx: number, action: string) => busyAction === `${idx}:${action}`;

  useEffect(() => showBackButton(() => goHome()), [navigate]);

  useEffect(() => {
    if (!scenarioKey) return;
    let cancelled = false;

    api.scenarios().then((cat) => {
      if (cancelled) return;
      const all = [...cat.exam, ...cat.daily];
      const s = all.find((x) => x.key === scenarioKey);
      if (s) setTitleLv(s.title_lv);
    });

    api.startChat(scenarioKey)
      .then(({ session_id, reply }) => {
        if (cancelled) return;
        setSessionId(session_id);
        setMessages([{ role: "assistant", text: reply }]);
      })
      .catch((e) => {
        if (!cancelled) setErr(String(e));
      });

    return () => {
      cancelled = true;
    };
  }, [scenarioKey]);

  useEffect(() => {
    messagesRef.current?.scrollTo({
      top: messagesRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, awaitingReply]);

  async function send(text: string) {
    if (!sessionId || !scenarioKey) return;
    setMessages((prev) => [...prev, { role: "user", text }]);
    setAwaitingReply(true);
    try {
      const { reply } = await api.sendChat(sessionId, text);
      setMessages((prev) => [...prev, { role: "assistant", text: reply }]);
      haptic("light");
      saveActive({
        mode: "dialog",
        sessionId,
        scenario: scenarioKey,
        route: `/chat/${scenarioKey}`,
      });
    } finally {
      setAwaitingReply(false);
    }
  }

  useEffect(() => {
    return () => {
      // Clearing on unmount is too aggressive — we want to keep the "resume"
      // banner useful after the user closes the Mini App. Only clear when they
      // explicitly go home via the back button.
    };
  }, []);

  // Expose an explicit "end" via back arrow
  function goHome() {
    clearActive();
    navigate("/");
  }

  async function finish() {
    if (!sessionId || finishing) return;
    setFinishing(true);
    haptic("heavy");
    try {
      const { report } = await api.finishChat(sessionId);
      setReport(report);
      clearActive();
    } catch (e) {
      setErr(String(e));
    } finally {
      setFinishing(false);
    }
  }

  async function playTts(msgIdx: number, speed: number = 1.0) {
    const key = speed < 1 ? "slow" : "play";
    if (isBusy(msgIdx, key)) return;
    haptic("soft");
    setBusyAction(`${msgIdx}:${key}`);
    try {
      const url = await api.ttsUrl(stripMarkup(messages[msgIdx].text), speed);
      const audio = new Audio(url);
      audio.onended = () => setBusyAction(null);
      audio.onerror = () => setBusyAction(null);
      await audio.play();
    } catch (e) {
      setErr(String(e));
      setBusyAction(null);
    }
  }

  async function loadHint(msgIdx: number) {
    if (isBusy(msgIdx, "hint")) return;
    haptic("soft");
    const msg = messages[msgIdx];
    if (msg.hint) return;
    setBusyAction(`${msgIdx}:hint`);
    try {
      const { hint } = await api.hint(stripMarkup(msg.text));
      setMessages((prev) => {
        const copy = [...prev];
        copy[msgIdx] = { ...copy[msgIdx], hint };
        return copy;
      });
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusyAction(null);
    }
  }

  function openSaveSheet(msgIdx: number) {
    haptic("soft");
    const text = messages[msgIdx].text;
    const bolded = text.match(/\*\*(.+?)\*\*/);
    const suggested = bolded ? bolded[1] : firstContentWord(text);
    setSaveSheet({ word: suggested, example: stripMarkup(text).slice(0, 200) });
  }

  if (report) {
    return (
      <DialogReportView
        titleLv={titleLv}
        report={report}
        onBack={goHome}
      />
    );
  }

  return (
    <div className="screen screen--chat">
      <div className="topbar">
        <button className="icon-pill" onClick={goHome} aria-label="Atpakaļ">‹</button>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="topbar-title">{titleLv || "…"}</div>
          <div className="topbar-sub">Sarunu režīms</div>
        </div>
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

      <div className="chat-messages" ref={messagesRef}>
        {messages.map((m, i) => (
          <div key={i} className="chat-group">
            <div
              className={`msg ${m.role}`}
              dangerouslySetInnerHTML={{ __html: renderInline(m.text) }}
            />
            {m.role === "assistant" && (
              <div className="msg-actions">
                <button className="msg-action" onClick={() => playTts(i)} disabled={isBusy(i, "play")}>
                  {isBusy(i, "play") ? "…" : "🔊"}
                </button>
                <button className="msg-action" onClick={() => playTts(i, 0.8)} disabled={isBusy(i, "slow")}>
                  {isBusy(i, "slow") ? "…" : "🐢"}
                </button>
                <button className="msg-action" onClick={() => loadHint(i)} disabled={isBusy(i, "hint")}>
                  {isBusy(i, "hint") ? "… перевожу" : "❓ krieviski"}
                </button>
                <button className="msg-action" onClick={() => openSaveSheet(i)}>🔖 saglabāt</button>
              </div>
            )}
            {m.hint && <div className="hint-block">{m.hint}</div>}
          </div>
        ))}
        {awaitingReply && (
          <div className="typing"><span /><span /><span /></div>
        )}
      </div>

      <InputBar
        scenario={scenarioKey || ""}
        placeholder="Rakstiet latviski…"
        disabled={awaitingReply || !sessionId}
        onSend={send}
      />

      {saveSheet && (
        <SaveWordSheet
          initialWord={saveSheet.word}
          initialExample={saveSheet.example}
          topic={scenarioKey}
          onClose={() => setSaveSheet(null)}
        />
      )}
    </div>
  );
}

function stripMarkup(s: string): string {
  return s.replace(/\*\*/g, "").replace(/💡 Dabiskāk:.*$/s, "").trim();
}

function firstContentWord(s: string): string {
  // pick the first "word-ish" token as a sensible default for the save sheet
  const cleaned = stripMarkup(s).replace(/[.,!?;:«»"']/g, " ");
  const token = cleaned.split(/\s+/).find((t) => t.length > 2);
  return token || "";
}

function renderInline(s: string): string {
  const esc = s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  return esc.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
}

function DialogReportView({
  titleLv,
  report,
  onBack,
}: {
  titleLv: string;
  report: Report;
  onBack: () => void;
}) {
  return (
    <div className="screen">
      <div className="topbar">
        <button className="icon-pill" onClick={onBack}>‹</button>
        <div style={{ flex: 1 }}>
          <div className="topbar-title">Разбор диалога</div>
          <div className="topbar-sub">{titleLv}</div>
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

        {report.summary_ru && (
          <div className="report-card">
            <h3>Итог</h3>
            <div>{report.summary_ru}</div>
          </div>
        )}

        {report.strengths_ru?.length > 0 && (
          <div className="report-card">
            <h3>Что получалось</h3>
            <ul style={{ margin: 0, paddingLeft: 18, fontSize: 14, lineHeight: 1.5 }}>
              {report.strengths_ru.map((s, i) => (
                <li key={i} style={{ marginBottom: 4 }}>{s}</li>
              ))}
            </ul>
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

        {report.new_vocabulary?.length > 0 && (
          <div className="report-card">
            <h3>Полезные слова из диалога</h3>
            <ul style={{ margin: 0, paddingLeft: 18, fontSize: 14, lineHeight: 1.5 }}>
              {report.new_vocabulary.map((w, i) => (
                <li key={i} style={{ marginBottom: 4 }}>{w}</li>
              ))}
            </ul>
          </div>
        )}

        {report.tips_ru?.length > 0 && (
          <div className="report-card">
            <h3>Над чем поработать</h3>
            <ul style={{ margin: 0, paddingLeft: 18, fontSize: 14, lineHeight: 1.5 }}>
              {report.tips_ru.map((t, i) => (
                <li key={i} style={{ marginBottom: 4 }}>{t}</li>
              ))}
            </ul>
          </div>
        )}

        <button className="btn btn-block" onClick={onBack}>Готово</button>
      </div>
    </div>
  );
}
