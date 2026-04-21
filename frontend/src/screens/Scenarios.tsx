import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api, ScenarioCatalog, ScenarioSummary } from "../api";
import { haptic } from "../tg";

type Tab = "exam" | "daily";

export default function Scenarios() {
  const [catalog, setCatalog] = useState<ScenarioCatalog | null>(null);
  const [tab, setTab] = useState<Tab>("exam");
  const [error, setError] = useState<string | null>(null);
  const [params] = useSearchParams();
  const navigate = useNavigate();

  useEffect(() => {
    api.scenarios()
      .then(setCatalog)
      .catch((e) => setError(String(e)));
  }, []);

  // Deep-link: ?scenario=transports opens directly
  useEffect(() => {
    const key = params.get("scenario");
    if (!key || !catalog) return;
    const inExam = catalog.exam.find((s) => s.key === key);
    const inDaily = catalog.daily.find((s) => s.key === key);
    if (inExam) navigate(`/exam/${key}`);
    else if (inDaily) navigate(`/chat/${key}`);
  }, [params, catalog, navigate]);

  if (error) {
    return (
      <div className="screen">
        <div className="toast">{error}</div>
      </div>
    );
  }
  if (!catalog) return <div className="screen"><div className="loader">Ielādē…</div></div>;

  const list: ScenarioSummary[] = tab === "exam" ? catalog.exam : catalog.daily;

  return (
    <div className="screen">
      <div className="title">
        Lvaloda <span className="title-accent">🇱🇻</span>
      </div>
      <div className="subtitle">Разговорная практика латышского</div>

      <button
        className="cta-exam"
        onClick={() => {
          haptic("medium");
          navigate(`/exam/random`);
        }}
      >
        <div className="cta-exam-title">🎓 Eksāmena simulācija</div>
        <div className="cta-exam-sub">
          Случайная тема · глубокая беседа с follow-up · разбор в конце
        </div>
      </button>

      <div className="tabs" role="tablist">
        <button
          role="tab"
          aria-selected={tab === "exam"}
          className={"tab " + (tab === "exam" ? "active" : "")}
          onClick={() => setTab("exam")}
        >
          Eksāmena tēmas
        </button>
        <button
          role="tab"
          aria-selected={tab === "daily"}
          className={"tab " + (tab === "daily" ? "active" : "")}
          onClick={() => setTab("daily")}
        >
          Ikdienas situācijas
        </button>
      </div>

      <div className="scenarios">
        {list.map((s) => (
          <button
            key={s.key}
            className="scenario-card"
            onClick={() => {
              haptic("light");
              navigate(tab === "exam" ? `/exam/${s.key}` : `/chat/${s.key}`);
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
