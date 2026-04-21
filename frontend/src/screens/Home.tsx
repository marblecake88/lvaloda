import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { ActiveSession, clearActive, loadActive } from "../cloud";
import { haptic } from "../tg";

interface Stats {
  streak: number;
  goal_minutes: number;
  today_minutes: number;
  week_days_active: number;
}

export default function Home() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<Stats | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [resume, setResume] = useState<ActiveSession | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.statsSummary()
      .then((s) => {
        if (!cancelled) setStats(s);
      })
      .catch((e) => {
        if (!cancelled) setErr(String(e));
      });
    loadActive().then((s) => {
      if (!cancelled && s) setResume(s);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const todayMin = stats?.today_minutes ?? 0;
  const goalMin = stats?.goal_minutes ?? 15;
  const progress = Math.min(1, todayMin / goalMin);

  return (
    <div className="screen">
      {err && <div className="toast" onClick={() => setErr(null)}>{err}</div>}

      <div className="home-heading">
        <span className="lv-flag" aria-hidden>
          <span />
          <span />
          <span />
        </span>
        <div>
          <div className="title">Lvaloda</div>
          <div className="subtitle" style={{ marginBottom: 0 }}>
            Ikdienas prakse
          </div>
        </div>
      </div>

      {resume && (
        <div className="resume-banner">
          <div className="resume-main">
            <div className="resume-label">Nepabeigta sesija</div>
            <div className="resume-topic">
              {resume.mode === "exam" ? "🎓 " : "💬 "}{resume.scenario}
            </div>
          </div>
          <div className="resume-actions">
            <button
              className="btn ghost"
              style={{ padding: "6px 10px", fontSize: 12 }}
              onClick={async () => {
                await clearActive();
                setResume(null);
              }}
            >
              Aizvērt
            </button>
            <button
              className="btn"
              style={{ padding: "6px 12px", fontSize: 12 }}
              onClick={() => {
                haptic("medium");
                navigate(resume.route);
              }}
            >
              Turpināt →
            </button>
          </div>
        </div>
      )}

      <div className="streak-card">
        <div className="streak-main">
          <div className="streak-fire">🔥</div>
          <div>
            <div className="streak-number">{stats?.streak ?? "…"}</div>
            <div className="streak-label">
              {stats?.streak === 1 ? "diena pēc kārtas" : "dienas pēc kārtas"}
            </div>
          </div>
        </div>
        <div className="progress-label">
          Šodien: <strong>{todayMin} / {goalMin} min</strong>
        </div>
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${progress * 100}%` }} />
        </div>
      </div>

      <button
        className="cta-exam"
        onClick={() => {
          haptic("medium");
          navigate(`/exam/random`);
        }}
      >
        <div className="cta-exam-title">🎓 Eksāmena simulācija</div>
        <div className="cta-exam-sub">
          Dziļa saruna · follow-up jautājumi · gala atskaite
        </div>
      </button>

      <div className="mode-grid">
        <button
          className="mode-card"
          data-accent="blue"
          onClick={() => navigate("/chat")}
        >
          <div className="mode-icon">💬</div>
          <div className="mode-title">Saruna</div>
          <div className="mode-sub">Saruna par tēmu</div>
        </button>
        <button
          className="mode-card"
          data-accent="red"
          onClick={() => navigate("/reading")}
        >
          <div className="mode-icon">📖</div>
          <div className="mode-title">Lasīšana</div>
          <div className="mode-sub">Teksts + 5 jautājumi</div>
        </button>
        <button
          className="mode-card"
          data-accent="purple"
          onClick={() => navigate("/phrases")}
        >
          <div className="mode-icon">⭐</div>
          <div className="mode-title">Top frāzes</div>
          <div className="mode-sub">Biežākās frāzes</div>
        </button>
        <button
          className="mode-card"
          data-accent="green"
          onClick={() => navigate("/shadowing")}
        >
          <div className="mode-icon">🗣</div>
          <div className="mode-title">Shadowing</div>
          <div className="mode-sub">Atkārto pēc bota</div>
        </button>
        <button
          className="mode-card"
          data-accent="orange"
          onClick={() => navigate("/picture")}
        >
          <div className="mode-icon">🖼</div>
          <div className="mode-title">Attēls</div>
          <div className="mode-sub">Apraksti attēlu</div>
        </button>
      </div>

      <div className="links-row">
        <Link to="/vocabulary" className="text-link">📚 Vārdnīca</Link>
        <Link to="/stats" className="text-link">📊 Statistika</Link>
        <Link to="/translate" className="text-link">🌐 Tulkotājs</Link>
      </div>
    </div>
  );
}
