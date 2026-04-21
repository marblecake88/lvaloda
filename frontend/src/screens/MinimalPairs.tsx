import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { haptic, notify, showBackButton } from "../tg";

interface Pair {
  a: string;
  b: string;
  a_ru: string;
  b_ru: string;
  note_ru: string;
  correct: "a" | "b";
}

export default function MinimalPairs() {
  const navigate = useNavigate();
  const [pair, setPair] = useState<Pair | null>(null);
  const [guessed, setGuessed] = useState<"a" | "b" | null>(null);
  const [score, setScore] = useState({ right: 0, total: 0 });
  const [err, setErr] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);

  useEffect(() => showBackButton(() => navigate("/")), [navigate]);

  async function loadNext() {
    setGuessed(null);
    try {
      const p = await api.minimalPairNext();
      setPair(p);
    } catch (e) {
      setErr(String(e));
    }
  }

  useEffect(() => {
    loadNext();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function playWhich(which: "a" | "b") {
    if (!pair) return;
    haptic("soft");
    setPlaying(true);
    try {
      const text = which === "a" ? pair.a : pair.b;
      const url = await api.ttsUrl(text);
      const audio = new Audio(url);
      audio.onended = () => setPlaying(false);
      await audio.play();
    } catch (e) {
      setErr(String(e));
      setPlaying(false);
    }
  }

  async function playMystery() {
    if (!pair) return;
    haptic("medium");
    setPlaying(true);
    try {
      const text = pair.correct === "a" ? pair.a : pair.b;
      const url = await api.ttsUrl(text);
      const audio = new Audio(url);
      audio.onended = () => setPlaying(false);
      await audio.play();
    } catch (e) {
      setErr(String(e));
      setPlaying(false);
    }
  }

  function guess(choice: "a" | "b") {
    if (!pair || guessed) return;
    haptic("medium");
    setGuessed(choice);
    const right = choice === pair.correct;
    setScore((s) => ({ right: s.right + (right ? 1 : 0), total: s.total + 1 }));
    notify(right ? "success" : "error");
  }

  if (err) return <div className="screen"><div className="toast">{err}</div></div>;
  if (!pair) {
    return <div className="screen"><div className="loader">Ielādē…</div></div>;
  }

  const isRight = guessed && guessed === pair.correct;

  return (
    <div className="screen">
      <div className="topbar">
        <button className="icon-pill" onClick={() => navigate("/")}>‹</button>
        <div style={{ flex: 1 }}>
          <div className="topbar-title">🎧 Minimālie pāri</div>
          <div className="topbar-sub">
            Счёт: {score.right} / {score.total}
          </div>
        </div>
      </div>

      <div className="report-card">
        <h3>Шаг 1 — послушай оба варианта</h3>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            className="btn ghost"
            style={{ flex: 1, fontSize: 16, padding: "14px 8px" }}
            onClick={() => playWhich("a")}
            disabled={playing}
          >
            🔊 {pair.a}
          </button>
          <button
            className="btn ghost"
            style={{ flex: 1, fontSize: 16, padding: "14px 8px" }}
            onClick={() => playWhich("b")}
            disabled={playing}
          >
            🔊 {pair.b}
          </button>
        </div>
        <div style={{ fontSize: 12, color: "var(--text-dim)", marginTop: 8 }}>
          {pair.a} — {pair.a_ru} · {pair.b} — {pair.b_ru}
        </div>
      </div>

      <div className="report-card">
        <h3>Шаг 2 — угадай что произнёс бот</h3>
        <button
          className="btn btn-block"
          onClick={playMystery}
          disabled={playing}
          style={{ marginBottom: 10 }}
        >
          🎧 Играть загадку
        </button>

        <div style={{ display: "flex", gap: 8 }}>
          <button
            className={"btn ghost" + (guessed === "a" ? " " : "")}
            style={{
              flex: 1,
              fontSize: 16,
              padding: 14,
              ...(guessed === "a" && pair.correct === "a"
                ? { borderColor: "#4caf50", color: "#2e7d32" }
                : guessed === "a"
                ? { borderColor: "var(--danger)", color: "var(--danger)" }
                : {}),
            }}
            onClick={() => guess("a")}
            disabled={!!guessed}
          >
            {pair.a}
          </button>
          <button
            className="btn ghost"
            style={{
              flex: 1,
              fontSize: 16,
              padding: 14,
              ...(guessed === "b" && pair.correct === "b"
                ? { borderColor: "#4caf50", color: "#2e7d32" }
                : guessed === "b"
                ? { borderColor: "var(--danger)", color: "var(--danger)" }
                : {}),
            }}
            onClick={() => guess("b")}
            disabled={!!guessed}
          >
            {pair.b}
          </button>
        </div>

        {guessed && (
          <div
            style={{
              marginTop: 12,
              padding: 12,
              borderRadius: 10,
              background: isRight ? "rgba(76,175,80,0.08)" : "rgba(224,79,79,0.08)",
              fontSize: 14,
            }}
          >
            <strong>{isRight ? "Pareizi!" : "Kļūda."}</strong> Правильный —{" "}
            <strong>{pair.correct === "a" ? pair.a : pair.b}</strong>.
            <div style={{ color: "var(--text-dim)", marginTop: 4, fontSize: 13 }}>
              {pair.note_ru}
            </div>
          </div>
        )}
      </div>

      {guessed && (
        <button className="btn btn-block" onClick={loadNext}>
          Следующая →
        </button>
      )}
    </div>
  );
}
