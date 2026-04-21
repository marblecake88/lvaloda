import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { haptic, showBackButton } from "../tg";

interface Item {
  id: string;
  title_lv: string;
  topic: string;
  topic_title_lv: string;
  preview: string;
  source: string | null;
}

export default function ReadingPicker() {
  const navigate = useNavigate();
  const [topics, setTopics] = useState<Record<string, string>>({});
  const [items, setItems] = useState<Item[]>([]);
  const [filter, setFilter] = useState<string>("all");
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => showBackButton(() => navigate("/")), [navigate]);

  useEffect(() => {
    let cancelled = false;
    api.readingTexts()
      .then((r) => {
        if (cancelled) return;
        setTopics(r.topics);
        setItems(r.items);
      })
      .catch((e) => !cancelled && setErr(String(e)));
    return () => {
      cancelled = true;
    };
  }, []);

  const visible = useMemo(
    () => (filter === "all" ? items : items.filter((it) => it.topic === filter)),
    [items, filter]
  );

  function pick(id: string) {
    haptic("medium");
    navigate(`/reading/${id}`);
  }

  return (
    <div className="screen">
      <div className="home-heading">
        <div>
          <div className="title">📖 Lasīšana</div>
          <div className="subtitle">
            Izlasi tekstu un atbildi uz 5 jautājumiem · PMLP 1. uzdevums
          </div>
        </div>
      </div>

      {err && <div className="toast" onClick={() => setErr(null)}>{err}</div>}

      <button
        className="cta-exam"
        onClick={() => pick("random")}
        style={{ marginBottom: 14 }}
      >
        <div className="cta-exam-title">🎲 Nejaušs teksts</div>
        <div className="cta-exam-sub">
          Pilns cikls · teksts + 5 jautājumi + atskaite
        </div>
      </button>

      <div className="chips" style={{ overflowX: "auto", marginBottom: 10 }}>
        <button
          className={`preset-chip${filter === "all" ? " preset-chip--active" : ""}`}
          onClick={() => setFilter("all")}
        >
          Visi ({items.length})
        </button>
        {Object.entries(topics).map(([key, label]) => {
          const count = items.filter((it) => it.topic === key).length;
          if (!count) return null;
          const short = label.split("(")[0].trim();
          return (
            <button
              key={key}
              className={`preset-chip${filter === key ? " preset-chip--active" : ""}`}
              onClick={() => setFilter(key)}
            >
              {short} ({count})
            </button>
          );
        })}
      </div>

      <div className="reading-list">
        {visible.map((it) => (
          <button key={it.id} className="reading-card" onClick={() => pick(it.id)}>
            <div className="reading-card-head">
              <div className="reading-card-title">{it.title_lv}</div>
              {it.source && <span className="reading-card-badge">PMLP</span>}
            </div>
            <div className="reading-card-topic">{it.topic_title_lv.split("(")[0].trim()}</div>
            <div className="reading-card-preview">{it.preview}</div>
          </button>
        ))}
        {!visible.length && !err && (
          <div className="empty">Nav tekstu šajā kategorijā.</div>
        )}
      </div>
    </div>
  );
}
