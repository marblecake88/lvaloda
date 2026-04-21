import { useEffect, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { haptic, notify } from "../tg";

/**
 * Quick 30-second post-session reflection. Research: metacognitive reflection
 * significantly improves retention. Skippable — user can just hit "пропустить".
 */
export default function Reflection() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state || {}) as { reportPath?: string };
  const [text, setText] = useState("");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const nextPath = state.reportPath ?? "/";

  useEffect(() => {
    haptic("light");
  }, []);

  async function save() {
    if (!text.trim()) return skip();
    setSaving(true);
    try {
      await api.saveReflection(
        sessionId ? Number(sessionId) : null,
        text.trim()
      );
      notify("success");
      navigate(nextPath, { replace: true, state: location.state });
    } catch (e) {
      setErr(String(e));
    } finally {
      setSaving(false);
    }
  }

  function skip() {
    navigate(nextPath, { replace: true, state: location.state });
  }

  return (
    <div className="screen">
      {err && <div className="toast" onClick={() => setErr(null)}>{err}</div>}

      <div className="title">Reflex 30 sekundes</div>
      <div className="subtitle">
        Исследования: короткая рефлексия сразу после сессии закрепляет материал
        значительно лучше, чем просто прочесть его ещё раз.
      </div>

      <div className="report-card">
        <h3>Что полезного вынес из этой сессии?</h3>
        <textarea
          className="text-input"
          style={{ width: "100%", minHeight: 120, padding: 14 }}
          placeholder="Новое слово, неожиданная формулировка, ошибка которую запомнил…"
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={5}
          autoFocus
        />
      </div>

      <div style={{ display: "flex", gap: 8 }}>
        <button className="btn ghost" onClick={skip} disabled={saving} style={{ flex: 1 }}>
          Пропустить
        </button>
        <button className="btn" onClick={save} disabled={saving} style={{ flex: 2 }}>
          {saving ? "…" : "Сохранить"}
        </button>
      </div>
    </div>
  );
}
