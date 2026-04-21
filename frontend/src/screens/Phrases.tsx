import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { haptic, notify, showBackButton } from "../tg";

interface Category {
  key: string;
  title_lv: string;
  title_ru: string;
  count: number;
  last_run: { known: number; total: number; at: string } | null;
}

export default function Phrases() {
  const navigate = useNavigate();
  const [cats, setCats] = useState<Category[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => showBackButton(() => navigate("/")), [navigate]);

  useEffect(() => {
    let cancelled = false;
    api.phraseCategories()
      .then((r) => !cancelled && setCats(r.categories))
      .catch((e) => !cancelled && setErr(String(e)));
    return () => {
      cancelled = true;
    };
  }, []);

  if (err) return <div className="screen"><div className="toast">{err}</div></div>;
  if (!cats) return <div className="screen"><div className="loader">Ielādē…</div></div>;

  const total = cats.reduce((s, c) => s + c.count, 0);

  return (
    <div className="screen">
      <div className="topbar">
        <button className="icon-pill" onClick={() => navigate("/")}>‹</button>
        <div className="topbar-title">⭐ Top frāzes</div>
      </div>

      <div className="subtitle" style={{ marginBottom: 12, color: "var(--text-dim)" }}>
        {total} biežāk lietotās latviešu frāzes, sadalītas pa tēmām.
        Vienā sesijā — 10 nejauši izvēlētas kartes.
      </div>

      <div className="scenarios">
        {cats.map((c) => (
          <button
            key={c.key}
            className="scenario-card"
            onClick={() => {
              haptic("light");
              navigate(`/phrases/${c.key}`);
            }}
          >
            <div style={{ minWidth: 0, flex: 1 }}>
              <div className="scenario-title">{c.title_lv}</div>
              <div className="scenario-sub">
                {c.title_ru} · {c.count} vārdi
              </div>
            </div>
            {c.last_run && (
              <div className="last-run-badge" title={c.last_run.at}>
                {c.last_run.known}/{c.last_run.total}
              </div>
            )}
            <div className="scenario-arrow">›</div>
          </button>
        ))}
      </div>
    </div>
  );
}

/**
 * Flashcard drill within a single category.
 * Cycles through phrases; items marked "not yet" go back into the deck.
 */
export function PhraseDrill() {
  const navigate = useNavigate();
  const pathParts = window.location.pathname.split("/");
  const category = decodeURIComponent(pathParts[pathParts.length - 1]);

  const [deck, setDeck] = useState<{ lv: string; ru: string; hint_ru: string | null }[]>([]);
  const [queue, setQueue] = useState<number[]>([]);
  const [curIdx, setCurIdx] = useState<number | null>(null);
  const [flipped, setFlipped] = useState(false);
  const [score, setScore] = useState({ known: 0, total: 0 });
  const [done, setDone] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // Undo stack: one snapshot per "next" press so we can step back.
  type Snapshot = {
    curIdx: number;
    queue: number[];
    score: { known: number; total: number };
    done: boolean;
  };
  const [undo, setUndo] = useState<Snapshot[]>([]);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [runSaved, setRunSaved] = useState(false);
  const [runs, setRuns] = useState<
    { id: number; total: number; known: number; created_at: string }[]
  >([]);

  useEffect(() => showBackButton(() => navigate("/phrases")), [navigate]);

  const SESSION_SIZE = 10;

  function sampleDeck(items: { lv: string; ru: string; hint_ru: string | null }[]) {
    const shuffled = [...items].sort(() => Math.random() - 0.5);
    return shuffled.slice(0, Math.min(SESSION_SIZE, shuffled.length));
  }

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.phrasesIn(category), api.phraseRuns(category, 10)])
      .then(([r, rr]) => {
        if (cancelled) return;
        const sampled = sampleDeck(r.items);
        setDeck(sampled);
        const order = sampled.map((_, i) => i);
        setQueue(order);
        setCurIdx(order[0] ?? null);
        setStartedAt(Date.now());
        setRuns(rr.runs);
      })
      .catch((e) => !cancelled && setErr(String(e)));
    return () => {
      cancelled = true;
    };
  }, [category]);

  const cur = curIdx !== null ? deck[curIdx] : null;

  function next(markKnown: boolean) {
    if (curIdx === null) return;
    haptic(markKnown ? "light" : "soft");

    // Snapshot BEFORE mutating so the back button can restore this exact state.
    setUndo((prev) => [...prev, { curIdx, queue, score, done }]);

    setScore((s) => ({
      known: s.known + (markKnown ? 1 : 0),
      total: s.total + 1,
    }));

    // One-pass mode: regardless of known/unknown, the card leaves the deck.
    // Unknown ones are tallied for the final score but not re-shown this run.
    const newQueue = queue.slice(1);
    setFlipped(false);

    if (newQueue.length === 0) {
      setDone(true);
      setCurIdx(null);
      notify("success");
      return;
    }
    setQueue(newQueue);
    setCurIdx(newQueue[0]);
  }

  function back() {
    if (undo.length === 0) return;
    haptic("soft");
    const prev = undo[undo.length - 1];
    setUndo((u) => u.slice(0, -1));
    setCurIdx(prev.curIdx);
    setQueue(prev.queue);
    setScore(prev.score);
    setDone(prev.done);
    setFlipped(false);
  }

  // Save a run once when the drill completes.
  useEffect(() => {
    if (!done || runSaved || deck.length === 0) return;
    const duration = startedAt
      ? Math.round((Date.now() - startedAt) / 1000)
      : undefined;
    setRunSaved(true);
    api.savePhraseRun({
      category,
      total: deck.length,
      known: score.known,
      duration_sec: duration,
    })
      .then(() => api.phraseRuns(category, 10))
      .then((rr) => setRuns(rr.runs))
      .catch(() => {
        // non-fatal
      });
  }, [done, runSaved, deck.length, startedAt, score.known, category]);

  async function playLv() {
    if (!cur) return;
    haptic("soft");
    try {
      const url = await api.ttsUrl(cur.lv);
      new Audio(url).play();
    } catch (e) {
      setErr(String(e));
    }
  }

  if (err) return <div className="screen"><div className="toast">{err}</div></div>;
  if (!deck.length) return <div className="screen"><div className="loader">Ielādē…</div></div>;

  if (done) {
    return (
      <div className="screen">
        <div className="topbar">
          <button className="icon-pill" onClick={() => navigate("/phrases")}>‹</button>
          <div className="topbar-title">Pabeigts</div>
        </div>

        <div className="report-card" style={{ textAlign: "center", padding: 28 }}>
          <div style={{ fontSize: 48, lineHeight: 1 }}>🎉</div>
          <h3 style={{ margin: "12px 0 6px" }}>Tēma pabeigta!</h3>
          <div className="report-score" style={{ marginTop: 8 }}>
            {score.known}
            <span className="report-score-max">/{deck.length}</span>
          </div>
          <div style={{ color: "var(--text-dim)", fontSize: 13, marginTop: 4 }}>
            zināji no {deck.length}
          </div>
        </div>

        {runs.length > 0 && (
          <div className="report-card">
            <h3>Pēdējie mēģinājumi</h3>
            <div className="runs-list">
              {runs.map((r, i) => {
                const pct = r.total > 0 ? r.known / r.total : 0;
                const isBest = r.known === Math.max(...runs.map((x) => x.known));
                return (
                  <div key={r.id} className="run-row">
                    <div className="run-index">{i === 0 ? "tagad" : `#${i + 1}`}</div>
                    <div className="run-bar">
                      <div
                        className="run-bar-fill"
                        style={{ width: `${pct * 100}%` }}
                      />
                    </div>
                    <div className="run-score">
                      {r.known}/{r.total}
                      {isBest && i !== 0 ? " 🏆" : ""}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        <div style={{ display: "flex", gap: 8 }}>
          <button
            className="btn ghost"
            style={{ flex: 1 }}
            onClick={async () => {
              haptic("medium");
              try {
                const r = await api.phrasesIn(category);
                const sampled = sampleDeck(r.items);
                setDeck(sampled);
                const order = sampled.map((_, i) => i);
                setQueue(order);
                setCurIdx(order[0]);
                setScore({ known: 0, total: 0 });
                setUndo([]);
                setDone(false);
                setFlipped(false);
                setRunSaved(false);
                setStartedAt(Date.now());
              } catch (e) {
                setErr(String(e));
              }
            }}
          >
            🔁 Vēl reizi
          </button>
          <button
            className="btn"
            style={{ flex: 1 }}
            onClick={() => navigate("/phrases")}
          >
            Uz tēmām
          </button>
        </div>
      </div>
    );
  }

  const totalInDeck = deck.length;
  const seen = totalInDeck - queue.length + 1;

  return (
    <div className="screen">
      <div className="topbar">
        <button className="icon-pill" onClick={() => navigate("/phrases")}>‹</button>
        <div style={{ flex: 1 }}>
          <div className="topbar-title">⭐ Frāzes</div>
          <div className="topbar-sub">
            {seen} / {totalInDeck} · zinu {score.known}
          </div>
        </div>
      </div>

      <div className="progress-bar" style={{ marginBottom: 12 }}>
        <div
          className="progress-fill"
          style={{ width: `${(seen / totalInDeck) * 100}%` }}
        />
      </div>

      <div style={{ display: "flex", marginBottom: 10 }}>
        <button
          className="btn ghost"
          style={{ padding: "6px 12px", fontSize: 13, opacity: undo.length ? 1 : 0.4 }}
          onClick={back}
          disabled={undo.length === 0}
        >
          ⟲ Atpakaļ
        </button>
      </div>

      {cur && (
        // key={curIdx} remounts the element on card change so the reverse-flip
        // animation doesn't briefly expose the next card's LV side.
        <div
          key={curIdx}
          className={"flashcard " + (flipped ? "flashcard--flipped" : "")}
          onClick={() => {
            setFlipped(!flipped);
            haptic("selection" as any);
          }}
        >
          <div className="flashcard-inner">
            <div className="flashcard-face flashcard-front">
              <div className="flashcard-label">RU</div>
              <div className="flashcard-text">{cur.ru}</div>
              <div className="flashcard-hint">Pieskaries, lai redzētu latviski</div>
            </div>
            <div className="flashcard-face flashcard-back">
              <div className="flashcard-label">LV</div>
              <div className="flashcard-text">{cur.lv}</div>
              {cur.hint_ru && <div className="flashcard-hint">{cur.hint_ru}</div>}
              <button
                className="btn ghost"
                style={{ marginTop: 14 }}
                onClick={(e) => {
                  e.stopPropagation();
                  playLv();
                }}
              >
                🔊 Klausīties
              </button>
            </div>
          </div>
        </div>
      )}

      <div style={{ display: "flex", gap: 10, marginTop: 16 }}>
        <button
          className="btn danger"
          style={{ flex: 1, fontSize: 15, padding: "14px" }}
          onClick={() => next(false)}
        >
          ✕ Nezinu
        </button>
        <button
          className="btn"
          style={{ flex: 1, fontSize: 15, padding: "14px" }}
          onClick={() => next(true)}
        >
          ✓ Zinu
        </button>
      </div>
    </div>
  );
}
