import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { useRecorder } from "../hooks/useRecorder";
import { haptic, notify, showBackButton } from "../tg";

type Phase = "listen" | "record" | "compare" | "done";

interface Phrase {
  lv: string;
  ru: string;
}

export default function Shadowing() {
  const { topicKey } = useParams();
  const navigate = useNavigate();
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [topicTitle, setTopicTitle] = useState<string>("");
  const [phrases, setPhrases] = useState<Phrase[]>([]);
  const [idx, setIdx] = useState(0);
  const [phase, setPhase] = useState<Phase>("listen");
  const [err, setErr] = useState<string | null>(null);
  const [userBlob, setUserBlob] = useState<Blob | null>(null);
  const [origUrl, setOrigUrl] = useState<string | null>(null);
  const rec = useRecorder();
  const cacheRef = useRef<Map<number, string>>(new Map());

  useEffect(() => showBackButton(() => navigate("/")), [navigate]);

  useEffect(() => {
    let cancelled = false;
    api.shadowingStart(topicKey === "random" ? undefined : topicKey)
      .then((res) => {
        if (cancelled) return;
        setSessionId(res.session_id);
        setTopicTitle(res.topic.title_lv);
        setPhrases(res.phrases);
      })
      .catch((e) => !cancelled && setErr(String(e)));
    return () => {
      cancelled = true;
    };
  }, [topicKey]);

  const cur = phrases[idx];

  async function getOrigUrl(speed = 1.0): Promise<string | null> {
    if (!sessionId) return null;
    const key = speed === 1.0 ? idx : -idx - 100;
    if (cacheRef.current.has(key)) return cacheRef.current.get(key)!;
    const url = await api.shadowingTtsUrl(sessionId, idx, speed);
    cacheRef.current.set(key, url);
    return url;
  }

  async function playOriginal(speed = 1.0) {
    haptic("soft");
    try {
      const url = await getOrigUrl(speed);
      if (!url) return;
      setOrigUrl(url);
      const audio = new Audio(url);
      await audio.play();
    } catch (e) {
      setErr(String(e));
    }
  }

  async function startRecord() {
    haptic("medium");
    setUserBlob(null);
    try {
      await rec.start();
      setPhase("record");
    } catch (e) {
      setErr(String(e));
    }
  }

  async function stopRecord() {
    const blob = await rec.stop();
    setUserBlob(blob);
    setPhase("compare");
    haptic("light");
  }

  async function playCompare() {
    haptic("soft");
    try {
      const origBlobUrl = await getOrigUrl();
      if (!origBlobUrl || !userBlob) return;
      const userUrl = URL.createObjectURL(userBlob);
      // Play orig, then user one after another.
      const orig = new Audio(origBlobUrl);
      const mine = new Audio(userUrl);
      orig.onended = () => {
        mine.play();
      };
      orig.play();
    } catch (e) {
      setErr(String(e));
    }
  }

  function next() {
    haptic("medium");
    setUserBlob(null);
    setOrigUrl(null);
    if (idx + 1 >= phrases.length) {
      setPhase("done");
      notify("success");
      return;
    }
    setIdx(idx + 1);
    setPhase("listen");
  }

  if (err) return <div className="screen"><div className="toast">{err}</div></div>;
  if (!cur) {
    return (
      <div className="screen">
        <div className="loader">Готовлю фразы…</div>
      </div>
    );
  }

  if (phase === "done") {
    return (
      <div className="screen">
        <div className="topbar">
          <button className="icon-pill" onClick={() => navigate("/")}>‹</button>
          <div className="topbar-title">🗣 {topicTitle}</div>
        </div>
        <div className="report-card" style={{ textAlign: "center", padding: 24 }}>
          <div style={{ fontSize: 48 }}>🎉</div>
          <h3 style={{ marginTop: 12 }}>Готово!</h3>
          <div style={{ color: "var(--text-dim)", fontSize: 14, margin: "8px 0 16px" }}>
            Прогнал {phrases.length} фраз. Отлично для слуха и прононса.
          </div>
          <button className="btn btn-block" onClick={() => navigate("/")}>На главную</button>
        </div>
      </div>
    );
  }

  return (
    <div className="screen">
      <div className="topbar">
        <button className="icon-pill" onClick={() => navigate("/")}>‹</button>
        <div style={{ flex: 1 }}>
          <div className="topbar-title">🗣 {topicTitle}</div>
          <div className="topbar-sub">Фраза {idx + 1} / {phrases.length}</div>
        </div>
      </div>

      <div className="progress-bar" style={{ marginBottom: 16 }}>
        <div
          className="progress-fill"
          style={{ width: `${((idx + 1) / phrases.length) * 100}%` }}
        />
      </div>

      <div className="report-card" style={{ textAlign: "center", padding: "22px 18px" }}>
        <div style={{ fontSize: 22, fontWeight: 600, lineHeight: 1.35 }}>{cur.lv}</div>
        <div style={{ color: "var(--text-dim)", fontSize: 14, marginTop: 8 }}>{cur.ru}</div>
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
        <button className="btn ghost" style={{ flex: 1 }} onClick={() => playOriginal()}>
          🔊 Оригинал
        </button>
        <button className="btn ghost" style={{ flex: 1 }} onClick={() => playOriginal(0.75)}>
          🐢 Медленно
        </button>
      </div>

      {phase === "listen" && (
        <button className="btn btn-block" onClick={startRecord}>
          🎙 Повторить
        </button>
      )}

      {phase === "record" && (
        <>
          <div className="rec-bar" style={{ marginBottom: 10 }}>
            <div className="rec-dot" />
            <div className="rec-time">{formatDur(rec.duration)}</div>
            <Meter levels={rec.levels} />
          </div>
          <button className="btn btn-block" onClick={stopRecord}>✓ Готово</button>
        </>
      )}

      {phase === "compare" && (
        <>
          <button className="btn btn-block" onClick={playCompare} style={{ marginBottom: 8 }}>
            🔁 Сравнить (оригинал → моя)
          </button>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn ghost" style={{ flex: 1 }} onClick={startRecord}>
              Перезаписать
            </button>
            <button className="btn" style={{ flex: 1 }} onClick={next}>
              Дальше →
            </button>
          </div>
        </>
      )}

      <div style={{ display: "none" }}>{origUrl}</div>
    </div>
  );
}

function Meter({ levels }: { levels: number[] }) {
  return (
    <div className="rec-meter">
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

function formatDur(sec: number) {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}
