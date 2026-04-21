import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { haptic, notify, showBackButton } from "../tg";

const PREP_SECONDS = 60;

interface PrepData {
  scenario: { key: string; title_lv: string; title_ru: string };
  chunks: { lv: string; ru: string }[];
  key_words: string[];
  sample_angles: string[];
}

export default function Prep() {
  const { topicKey } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState<PrepData | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [seconds, setSeconds] = useState(PREP_SECONDS);

  useEffect(() => showBackButton(() => navigate(-1)), [navigate]);

  useEffect(() => {
    if (!topicKey) return;
    let cancelled = false;
    api.prep(topicKey)
      .then((d) => !cancelled && setData(d))
      .catch((e) => !cancelled && setErr(String(e)));
    return () => {
      cancelled = true;
    };
  }, [topicKey]);

  useEffect(() => {
    const id = setInterval(() => setSeconds((s) => (s > 0 ? s - 1 : 0)), 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    if (seconds === 10) haptic("medium");
    if (seconds === 0) notify("success");
  }, [seconds]);

  function startExam() {
    haptic("heavy");
    navigate(`/exam/${topicKey}`);
  }

  async function playLv(text: string) {
    haptic("soft");
    try {
      const url = await api.ttsUrl(text);
      new Audio(url).play();
    } catch (e) {
      setErr(String(e));
    }
  }

  if (err) return <div className="screen"><div className="toast">{err}</div></div>;
  if (!data) {
    return (
      <div className="screen">
        <div className="loader">Готовлю материалы…</div>
      </div>
    );
  }

  return (
    <div className="screen">
      <div className="topbar">
        <button className="icon-pill" onClick={() => navigate(-1)}>‹</button>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="topbar-title">🎓 {data.scenario.title_lv}</div>
          <div className="topbar-sub">Подготовка · {data.scenario.title_ru}</div>
        </div>
      </div>

      <div className="prep-timer">
        <div className="prep-timer-num">{seconds}</div>
        <div className="prep-timer-label">секунд на чтение</div>
      </div>

      <div className="report-card">
        <h3>Полезные фразы</h3>
        {data.chunks.map((c, i) => (
          <div key={i} className="prep-chunk">
            <div className="prep-chunk-lv">
              {c.lv}
              <button className="msg-action" onClick={() => playLv(c.lv)}>🔊</button>
            </div>
            <div className="prep-chunk-ru">{c.ru}</div>
          </div>
        ))}
      </div>

      {data.key_words.length > 0 && (
        <div className="report-card">
          <h3>Ключевые слова</h3>
          <div className="chips">
            {data.key_words.map((w) => (
              <span key={w} className="chip" style={{ fontSize: 13, padding: "6px 12px" }}>
                {w}
              </span>
            ))}
          </div>
        </div>
      )}

      {data.sample_angles.length > 0 && (
        <div className="report-card">
          <h3>О чём могут спросить</h3>
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: 14, lineHeight: 1.5 }}>
            {data.sample_angles.map((a, i) => (
              <li key={i} style={{ marginBottom: 4 }}>{a}</li>
            ))}
          </ul>
        </div>
      )}

      <button className="btn btn-block" style={{ marginTop: 8 }} onClick={startExam}>
        Готов, начать 🚀
      </button>
    </div>
  );
}
