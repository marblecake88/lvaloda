import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { api, ScenarioCatalog, ScenarioSummary } from "../api";
import { useSwipe } from "../hooks/useSwipe";
import { haptic, showBackButton } from "../tg";

type Tab = "exam" | "daily";

interface Props {
  /** Which tab to open initially (based on route) */
  initialTab: Tab;
}

export default function ScenarioPicker({ initialTab }: Props) {
  const [catalog, setCatalog] = useState<ScenarioCatalog | null>(null);
  const [tab, setTab] = useState<Tab>(initialTab);
  const [err, setErr] = useState<string | null>(null);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => showBackButton(() => navigate("/")), [navigate]);

  useEffect(() => {
    let cancelled = false;
    api.scenarios()
      .then((c) => !cancelled && setCatalog(c))
      .catch((e) => !cancelled && setErr(String(e)));
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    setTab(initialTab);
  }, [initialTab, location.pathname]);

  // Horizontal swipe between the two tabs (exam ↔ daily).
  // Must be declared above the early returns to satisfy Rules of Hooks.
  const swipe = useSwipe({
    onLeft: () => {
      if (tab !== "daily") {
        haptic("soft");
        setTab("daily");
      }
    },
    onRight: () => {
      if (tab !== "exam") {
        haptic("soft");
        setTab("exam");
      }
    },
  });

  if (err) return <div className="screen"><div className="toast">{err}</div></div>;
  if (!catalog) return <div className="screen"><div className="loader">Ielādē…</div></div>;

  const list: ScenarioSummary[] = tab === "exam" ? catalog.exam : catalog.daily;

  function onPick(key: string) {
    haptic("light");
    if (tab === "exam") navigate(`/exam/prep/${key}`);
    else navigate(`/chat/${key}`);
  }

  return (
    <div className="screen" {...swipe}>
      <div className="topbar">
        <button className="icon-pill" onClick={() => navigate("/")}>‹</button>
        <div className="topbar-title">
          {tab === "exam" ? "Eksāmena tēmas" : "Ikdienas situācijas"}
        </div>
      </div>

      <div className="tabs">
        <button
          className={"tab " + (tab === "exam" ? "active" : "")}
          onClick={() => setTab("exam")}
        >
          Eksāmena tēmas
        </button>
        <button
          className={"tab " + (tab === "daily" ? "active" : "")}
          onClick={() => setTab("daily")}
        >
          Ikdienas situācijas
        </button>
      </div>

      <div className="scenarios">
        {list.map((s) => (
          <button key={s.key} className="scenario-card" onClick={() => onPick(s.key)}>
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
