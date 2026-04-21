import { useEffect, useRef, useState } from "react";
import { useRecorder } from "../hooks/useRecorder";
import { api } from "../api";
import { haptic, notify } from "../tg";

interface Props {
  scenario: string;          // scenario key (for STT biasing)
  placeholder: string;
  disabled?: boolean;
  onSend: (text: string) => void | Promise<void>;
}

/**
 * Input bar with three modes:
 *   idle → typing (text) or tap mic → recording → review → send/cancel/re-record
 *
 * In review mode the transcript is editable so the user can tweak typos
 * from Whisper before shipping to the LLM.
 */
export default function InputBar({ scenario, placeholder, disabled, onSend }: Props) {
  const [text, setText] = useState("");
  const [review, setReview] = useState<string | null>(null);
  const [sttBusy, setSttBusy] = useState(false);
  const [sending, setSending] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const rec = useRecorder();
  const taRef = useRef<HTMLTextAreaElement>(null);
  const reviewRef = useRef<HTMLTextAreaElement>(null);

  // Auto-grow textarea
  useEffect(() => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(140, ta.scrollHeight) + "px";
  }, [text]);

  useEffect(() => {
    const ta = reviewRef.current;
    if (!ta || review === null) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(160, ta.scrollHeight) + "px";
    ta.focus();
  }, [review]);

  useEffect(() => {
    if (rec.error) setErr(rec.error);
  }, [rec.error]);

  async function doSend(value: string) {
    if (!value.trim() || sending) return;
    setSending(true);
    try {
      await onSend(value.trim());
      setText("");
      setReview(null);
      haptic("light");
    } catch (e: any) {
      setErr(String(e?.message || e));
      notify("error");
    } finally {
      setSending(false);
    }
  }

  async function startRec() {
    haptic("medium");
    try {
      await rec.start();
    } catch {
      /* error already set by hook */
    }
  }

  async function stopAndTranscribe() {
    const blob = await rec.stop();
    haptic("light");
    if (blob.size === 0) return;
    setSttBusy(true);
    try {
      const transcript = await api.stt(blob, scenario);
      setReview(transcript);
    } catch (e: any) {
      setErr(String(e?.message || e));
      notify("error");
    } finally {
      setSttBusy(false);
    }
  }

  function cancelRec() {
    haptic("soft");
    rec.cancel();
  }

  async function reRecord() {
    setReview(null);
    await startRec();
  }

  // ---- RECORDING MODE ----
  if (rec.recording) {
    return (
      <div className="input-row">
        <button className="icon-btn ghost" onClick={cancelRec} aria-label="Отмена">✕</button>
        <div className="rec-bar">
          <div className="rec-dot" />
          <div className="rec-time">{formatDuration(rec.duration)}</div>
          <Meter levels={rec.levels} />
        </div>
        <button className="icon-btn" onClick={stopAndTranscribe} aria-label="Готово">✓</button>
      </div>
    );
  }

  // ---- REVIEW MODE (after STT) ----
  if (review !== null) {
    return (
      <>
        {err && <div className="toast" onClick={() => setErr(null)}>{err}</div>}
        <div className="review-card">
          <div className="review-label">Распознано — поправь или отправь</div>
          <textarea
            ref={reviewRef}
            className="review-text"
            value={review}
            onChange={(e) => setReview(e.target.value)}
            placeholder="…"
          />
          <div className="review-actions">
            <button className="btn danger" onClick={() => setReview(null)}>Отмена</button>
            <button className="btn ghost" onClick={reRecord} disabled={sending}>
              🎙 Перезаписать
            </button>
            <div className="spacer" />
            <button
              className="btn"
              onClick={() => doSend(review)}
              disabled={sending || !review.trim()}
            >
              {sending ? "…" : "Отправить ➤"}
            </button>
          </div>
        </div>
      </>
    );
  }

  // ---- IDLE / TYPING MODE ----
  return (
    <>
      {err && <div className="toast" onClick={() => setErr(null)}>{err}</div>}
      <div className="input-row">
        <textarea
          ref={taRef}
          className="text-input"
          placeholder={sttBusy ? "Распознаю…" : placeholder}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              doSend(text);
            }
          }}
          rows={1}
          disabled={disabled || sending || sttBusy}
        />
        {text.trim() ? (
          <button
            className="icon-btn"
            onClick={() => doSend(text)}
            disabled={sending || disabled}
            aria-label="Отправить"
          >
            ➤
          </button>
        ) : (
          <button
            className="icon-btn"
            onClick={startRec}
            disabled={disabled || sending || sttBusy}
            aria-label="Записать голос"
          >
            🎙
          </button>
        )}
      </div>
    </>
  );
}

function Meter({ levels }: { levels: number[] }) {
  return (
    <div className="rec-meter" aria-hidden>
      {levels.map((v, i) => (
        <span
          key={i}
          className={v > 0.08 ? "active" : ""}
          style={{ height: `${6 + v * 22}px`, opacity: 0.35 + v * 0.65 }}
        />
      ))}
    </div>
  );
}

function formatDuration(sec: number) {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}
