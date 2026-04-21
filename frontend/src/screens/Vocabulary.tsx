import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { haptic, showBackButton } from "../tg";

type Tab = "words" | "errors";

interface Word {
  id: number;
  word_lv: string;
  translation_ru: string;
  example: string | null;
  topic: string | null;
}

interface Err {
  id: number;
  said: string;
  better: string;
  note_ru: string | null;
  topic: string | null;
}

export default function Vocabulary() {
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>("words");
  const [words, setWords] = useState<Word[]>([]);
  const [errors, setErrors] = useState<Err[]>([]);
  const [loading, setLoading] = useState(true);
  const [apiErr, setApiErr] = useState<string | null>(null);

  useEffect(() => showBackButton(() => navigate("/")), [navigate]);

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.listWords(), api.listErrors()])
      .then(([w, e]) => {
        if (cancelled) return;
        setWords(w);
        setErrors(e);
      })
      .catch((e) => !cancelled && setApiErr(String(e)))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  async function removeWord(id: number) {
    haptic("soft");
    try {
      await api.deleteWord(id);
      setWords((prev) => prev.filter((w) => w.id !== id));
    } catch (e) {
      setApiErr(String(e));
    }
  }

  async function removeError(id: number) {
    haptic("soft");
    try {
      await api.deleteError(id);
      setErrors((prev) => prev.filter((w) => w.id !== id));
    } catch (e) {
      setApiErr(String(e));
    }
  }

  async function play(text: string) {
    haptic("soft");
    try {
      const url = await api.ttsUrl(text);
      new Audio(url).play();
    } catch (e) {
      setApiErr(String(e));
    }
  }

  return (
    <div className="screen">
      <div className="topbar">
        <button className="icon-pill" onClick={() => navigate("/")}>‹</button>
        <div className="topbar-title">Словарь и ошибки</div>
      </div>

      {apiErr && <div className="toast" onClick={() => setApiErr(null)}>{apiErr}</div>}

      <div className="tabs">
        <button
          className={"tab " + (tab === "words" ? "active" : "")}
          onClick={() => setTab("words")}
        >
          📚 Слова ({words.length})
        </button>
        <button
          className={"tab " + (tab === "errors" ? "active" : "")}
          onClick={() => setTab("errors")}
        >
          💡 Ошибки ({errors.length})
        </button>
      </div>

      {loading ? (
        <div className="loader">Ielādē…</div>
      ) : tab === "words" ? (
        <div className="scenarios">
          {words.length === 0 && (
            <div className="empty">
              Пока пусто. В чате нажимай 🔖 под ответом, чтобы сохранить слово.
            </div>
          )}
          {words.map((w) => (
            <div key={w.id} className="vocab-card">
              <div className="vocab-main">
                <div className="vocab-word">{w.word_lv}</div>
                <div className="vocab-trans">{w.translation_ru}</div>
                {w.example && <div className="vocab-example">«{w.example}»</div>}
              </div>
              <div className="vocab-actions">
                <button className="icon-pill" onClick={() => play(w.word_lv)}>🔊</button>
                <button className="icon-pill" onClick={() => removeWord(w.id)}>✕</button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="scenarios">
          {errors.length === 0 && (
            <div className="empty">
              Ошибок пока нет — они сюда автоматом собираются из «💡 Dabiskāk» в чате.
            </div>
          )}
          {errors.map((e) => (
            <div key={e.id} className="vocab-card">
              <div className="vocab-main">
                <div className="phrase-said">«{e.said}»</div>
                <div className="phrase-better">→ {e.better}</div>
                {e.note_ru && <div className="phrase-note">{e.note_ru}</div>}
              </div>
              <div className="vocab-actions">
                <button className="icon-pill" onClick={() => play(e.better)}>🔊</button>
                <button className="icon-pill" onClick={() => removeError(e.id)}>✕</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
