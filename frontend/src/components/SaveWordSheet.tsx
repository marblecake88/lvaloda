import { useState } from "react";
import { api } from "../api";
import { haptic, notify } from "../tg";

interface Props {
  initialWord: string;
  initialExample?: string;
  topic?: string;
  onClose: () => void;
}

export default function SaveWordSheet({
  initialWord,
  initialExample,
  topic,
  onClose,
}: Props) {
  const [word, setWord] = useState(initialWord.trim());
  const [translation, setTranslation] = useState("");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function save() {
    if (!word.trim() || !translation.trim()) {
      setErr("Нужны и слово, и перевод");
      return;
    }
    setSaving(true);
    haptic("medium");
    try {
      await api.addWord({
        word_lv: word.trim(),
        translation_ru: translation.trim(),
        example: initialExample,
        topic,
      });
      notify("success");
      onClose();
    } catch (e) {
      setErr(String(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <div className="sheet-backdrop" onClick={onClose} />
      <div className="sheet" role="dialog">
        <div className="sheet-handle" />
        <h3>Сохранить в словарь</h3>

        {err && <div className="toast" onClick={() => setErr(null)}>{err}</div>}

        <label className="review-label">Слово или фраза (latviski)</label>
        <input
          className="sheet-input"
          value={word}
          onChange={(e) => setWord(e.target.value)}
          placeholder="vārds vai frāze"
          autoFocus
        />

        <label className="review-label">Перевод / значение</label>
        <input
          className="sheet-input"
          value={translation}
          onChange={(e) => setTranslation(e.target.value)}
          placeholder="перевод на русский"
        />

        {initialExample && (
          <div style={{ fontSize: 12, color: "var(--text-dim)", marginTop: 4 }}>
            Пример: «{initialExample}»
          </div>
        )}

        <div className="sheet-row">
          <button className="btn ghost" onClick={onClose} disabled={saving}>
            Отмена
          </button>
          <div className="spacer" />
          <button className="btn" onClick={save} disabled={saving}>
            {saving ? "…" : "Сохранить"}
          </button>
        </div>
      </div>
    </>
  );
}
