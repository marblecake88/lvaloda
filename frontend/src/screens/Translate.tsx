import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useRecorder } from "../hooks/useRecorder";
import { haptic, notify, showBackButton } from "../tg";

interface Result {
  source_lang: string;
  source_text: string;
  translation: string;
}

export default function Translate() {
  const navigate = useNavigate();
  const [text, setText] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const rec = useRecorder();
  const taRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => showBackButton(() => navigate("/")), [navigate]);

  useEffect(() => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(200, ta.scrollHeight) + "px";
  }, [text]);

  async function translateText() {
    if (!text.trim() || loading) return;
    setLoading(true);
    haptic("light");
    try {
      const r = await api.translateText(text.trim());
      setResult(r);
      notify("success");
    } catch (e) {
      setErr(String(e));
      notify("error");
    } finally {
      setLoading(false);
    }
  }

  async function startRec() {
    haptic("medium");
    try {
      await rec.start();
    } catch {
      /* error surfaced by hook */
    }
  }

  async function stopAndTranslate() {
    const blob = await rec.stop();
    if (blob.size === 0) return;
    setLoading(true);
    haptic("light");
    try {
      const r = await api.translateAudio(blob);
      setText(r.source_text);
      setResult(r);
      notify("success");
    } catch (e) {
      setErr(String(e));
      notify("error");
    } finally {
      setLoading(false);
    }
  }

  function cancelRec() {
    rec.cancel();
  }

  async function playTranslation() {
    if (!result?.translation) return;
    haptic("soft");
    try {
      const url = await api.ttsUrl(result.translation);
      new Audio(url).play();
    } catch (e) {
      setErr(String(e));
    }
  }

  function swapInput() {
    if (!result) return;
    haptic("soft");
    setText(result.translation);
    setResult({
      source_lang: result.source_lang === "ru" ? "lv" : "ru",
      source_text: result.translation,
      translation: result.source_text,
    });
  }

  function clear() {
    setText("");
    setResult(null);
  }

  return (
    <div className="screen">
      <div className="topbar">
        <button className="icon-pill" onClick={() => navigate("/")}>‹</button>
        <div style={{ flex: 1 }}>
          <div className="topbar-title">🌐 Tulkotājs</div>
          <div className="topbar-sub">RU ↔ LV · автоопределение</div>
        </div>
        {(text || result) && (
          <button className="icon-pill" onClick={clear} aria-label="Очистить">✕</button>
        )}
      </div>

      {err && <div className="toast" onClick={() => setErr(null)}>{err}</div>}

      <div className="tr-card">
        <div className="tr-label">
          Ввод {result && <span className="tr-chip">{result.source_lang.toUpperCase()}</span>}
        </div>
        <textarea
          ref={taRef}
          className="tr-textarea"
          placeholder="Введи русский или латышский текст… или нажми 🎙"
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            if (result) setResult(null);
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
              e.preventDefault();
              translateText();
            }
          }}
          disabled={loading || rec.recording}
          rows={3}
        />

        {rec.recording ? (
          <div className="rec-bar" style={{ marginTop: 10 }}>
            <div className="rec-dot" />
            <div className="rec-time">
              {Math.floor(rec.duration / 60)}:
              {Math.floor(rec.duration % 60)
                .toString()
                .padStart(2, "0")}
            </div>
            <div className="rec-meter">
              {rec.levels.map((v, i) => (
                <span
                  key={i}
                  className={v > 0.08 ? "active" : ""}
                  style={{ height: `${6 + v * 22}px`, opacity: 0.35 + v * 0.65 }}
                />
              ))}
            </div>
            <button className="icon-btn ghost" onClick={cancelRec}>✕</button>
            <button className="icon-btn" onClick={stopAndTranslate}>✓</button>
          </div>
        ) : (
          <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
            <button
              className="btn ghost"
              onClick={startRec}
              disabled={loading}
              style={{ padding: "10px 14px" }}
            >
              🎙 Голос
            </button>
            <div className="spacer" />
            <button
              className="btn"
              onClick={translateText}
              disabled={loading || !text.trim()}
            >
              {loading ? "…" : "Tulkot →"}
            </button>
          </div>
        )}
      </div>

      {result && (
        <div className="tr-card tr-card--result">
          <div className="tr-label">
            Перевод{" "}
            <span className="tr-chip tr-chip--accent">
              {result.source_lang === "ru" ? "LV" : "RU"}
            </span>
          </div>
          <div className="tr-translation">{result.translation}</div>
          <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
            <button className="btn ghost" onClick={playTranslation}>
              🔊 Klausīties
            </button>
            <button className="btn ghost" onClick={swapInput}>
              ⇄ Поменять
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
