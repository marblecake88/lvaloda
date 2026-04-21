import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ScenarioSummary } from "../api";
import { haptic, showBackButton } from "../tg";

export default function ShadowingPicker() {
  const navigate = useNavigate();
  const [topics, setTopics] = useState<ScenarioSummary[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => showBackButton(() => navigate("/")), [navigate]);

  useEffect(() => {
    let cancelled = false;
    api.scenarios()
      .then((c) => !cancelled && setTopics(c.exam))
      .catch((e) => !cancelled && setErr(String(e)));
    return () => {
      cancelled = true;
    };
  }, []);

  if (err) return <div className="screen"><div className="toast">{err}</div></div>;
  if (!topics) return <div className="screen"><div className="loader">Ielādē…</div></div>;

  return (
    <div className="screen">
      <div className="topbar">
        <button className="icon-pill" onClick={() => navigate("/")}>‹</button>
        <div className="topbar-title">🗣 Shadowing</div>
      </div>

      <div className="subtitle" style={{ marginBottom: 16 }}>
        Слушай фразу → повтори → сравни. Лучший метод для прононса и слуха.
      </div>

      <button
        className="cta-exam"
        onClick={() => {
          haptic("medium");
          navigate("/shadowing/random");
        }}
      >
        <div className="cta-exam-title">🎲 Случайная тема</div>
        <div className="cta-exam-sub">Бот подберёт 8 фраз на любой теме</div>
      </button>

      <div className="scenarios">
        {topics.map((s) => (
          <button
            key={s.key}
            className="scenario-card"
            onClick={() => {
              haptic("light");
              navigate(`/shadowing/${s.key}`);
            }}
          >
            <div>
              <div className="scenario-title">{s.title_lv}</div>
              <div className="scenario-sub">{s.title_ru}</div>
            </div>
            <div className="scenario-arrow">›</div>
          </button>
        ))}
      </div>
    </div>
  );
}
