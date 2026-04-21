import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { showBackButton } from "../tg";

type StatsData = {
  streak: number;
  goal_minutes: number;
  today_minutes: number;
  today_messages: number;
  week_minutes: number;
  week_days_active: number;
  calendar: Record<string, { messages: number; minutes: number }>;
  topic_counts: Record<string, number>;
};

export default function Stats() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<StatsData | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => showBackButton(() => navigate("/")), [navigate]);

  useEffect(() => {
    let cancelled = false;
    api.statsSummary()
      .then((s) => !cancelled && setStats(s as StatsData))
      .catch((e) => !cancelled && setErr(String(e)));
    return () => {
      cancelled = true;
    };
  }, []);

  if (err) return <div className="screen"><div className="toast">{err}</div></div>;
  if (!stats) return <div className="screen"><div className="loader">Ielādē…</div></div>;

  // Build 30-day calendar grid (newest on the right)
  const days: Array<{ date: string; minutes: number }> = [];
  const today = new Date();
  for (let i = 29; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    const iso = d.toISOString().slice(0, 10);
    days.push({ date: iso, minutes: stats.calendar[iso]?.minutes ?? 0 });
  }
  const maxM = Math.max(1, ...days.map((d) => d.minutes));

  return (
    <div className="screen">
      <div className="topbar">
        <button className="icon-pill" onClick={() => navigate("/")}>‹</button>
        <div className="topbar-title">Статистика</div>
      </div>

      <div className="stats-row">
        <div className="stat-tile">
          <div className="stat-num">🔥 {stats.streak}</div>
          <div className="stat-label">стрик</div>
        </div>
        <div className="stat-tile">
          <div className="stat-num">{stats.today_minutes}</div>
          <div className="stat-label">мин сегодня</div>
        </div>
        <div className="stat-tile">
          <div className="stat-num">{stats.week_minutes}</div>
          <div className="stat-label">мин за неделю</div>
        </div>
      </div>

      <div className="report-card">
        <h3>Активность за 30 дней</h3>
        <div className="calendar">
          {days.map((d) => (
            <div
              key={d.date}
              className="cal-cell"
              title={`${d.date}: ${d.minutes} мин`}
              style={{
                opacity: d.minutes > 0 ? 0.3 + (d.minutes / maxM) * 0.7 : 0.08,
              }}
            />
          ))}
        </div>
        <div className="cal-legend">
          <span>30 дней назад</span>
          <span>сегодня</span>
        </div>
      </div>

      {Object.keys(stats.topic_counts).length > 0 && (
        <div className="report-card">
          <h3>Темы за последние 30 дней</h3>
          {Object.entries(stats.topic_counts)
            .sort(([, a], [, b]) => b - a)
            .map(([topic, count]) => (
              <div key={topic} className="topic-row">
                <div className="topic-name">{topic}</div>
                <div className="topic-bar">
                  <div
                    className="topic-bar-fill"
                    style={{
                      width: `${(count / Math.max(...Object.values(stats.topic_counts))) * 100}%`,
                    }}
                  />
                </div>
                <div className="topic-count">{count} дн.</div>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}
