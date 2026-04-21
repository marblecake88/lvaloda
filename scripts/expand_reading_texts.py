"""Pass 1 — expand each generated reading text by ~10-15%.

For every non-seed entry in backend/app/assets/reading_texts.py, ask Grok to
lengthen the body by 15-25 words by inserting ONE of: a concrete example,
a number/date, or a one-line expert voice. Questions, title, topic and
structure stay untouched. Seeds (PUTNI ZIEMĀ, CITRONS) are skipped — they
are the official PMLP paraugi.

Writes the catalog back in place. Re-run is idempotent only in the sense
that word counts won't blow up: the script refuses to accept bodies
outside 135-170 words.
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

from openai import OpenAI

from _reading_io import (  # type: ignore[import-not-found]
    count_words,
    is_seed,
    load_catalog,
    load_env,
    save_catalog,
)


SYSTEM_PROMPT = """Tu esi latviešu valodas eksāmenu tekstu redaktors. Tavs \
vienīgais uzdevums ir **nedaudz paplašināt** doto informatīvi-publicistisko \
tekstu, precīzi sasniedzot dototo mērķa vārdu skaitu.

KO DARI: Pievieno 1-2 teikumus (vai izvērs esošu teikumu), lai sasniegtu \
norādīto vārdu skaitu. Saturs — viens no:
1) Konkrēts piemērs (vietas nosaukums Latvijā, mēnesis, produkts, vecuma grupa).
2) Skaitlis / datums ("pēdējos 10 gados", "aptuveni 60 %", "3-4 reizes mēnesī").
3) Īss eksperta/speciālistu viedoklis ("Speciālisti iesaka…", "Pēc ... domām…").
4) Blakus detaļa, kas nostiprina galveno domu.

STINGRI SAGLABĀ:
- Virsrakstu (šeit tas nav jāatgriež).
- Galveno ideju un visus esošos faktus.
- Stilu un reģistru (A2-B1 informatīvi-publicistisks).
- Rindkopu skaitu — TIEŠI TĀDS PATS kā oriģinālā.

STINGRI AIZLIEGTS:
- Mainīt teksta struktūru.
- Izdzēst kādu no oriģinālā teikuma daļām.
- Rakstīt dialogu vai pirmajā personā.
- Pievienot vairāk par 2 teikumiem kopā.

MĒRĶA GARUMS — KRITISKI SVARĪGI:
Galīgajai versijai jābūt precīzi diapazonā, kas norādīts lietotāja ziņojumā \
(mērķa vārdu skaits). Saskaiti vārdus pirms atbildes sūtīšanas. Ja jūti, ka \
vārdu skaits nav diapazonā — koriģē, pirms atgriez.

ATBILDE — STINGRĀ JSON (bez Markdown, bez ``` blokiem):
{"body": "1. rindkopa.\\n\\n2. rindkopa.\\n\\n3. rindkopa.\\n\\n4. rindkopa."}
"""


def expand_one(client: OpenAI, model: str, text: dict[str, Any], retries: int = 2) -> str | None:
    old_n = count_words(text["body"])
    if old_n >= 135:
        return text["body"]  # already long enough, leave it
    target_low = 135
    target_high = 155
    old_paragraphs = text["body"].count("\n\n") + 1

    user_msg = (
        f"NOSAUKUMS: {text['title_lv']}\n\n"
        f"ORIĢINĀLS ({old_n} vārdi, {old_paragraphs} rindkopas):\n"
        f"---\n{text['body']}\n---\n\n"
        f"MĒRĶIS: paplašini līdz **{target_low}-{target_high} vārdiem** "
        f"(jāpievieno aptuveni {140 - old_n} vārdi — konkrēti piemēri, "
        f"skaitļi, eksperta viedoklis, blakus detaļas). "
        f"Saglabā {old_paragraphs} rindkopas. Nemainīgs oriģinālais saturs. "
        f"Atgriez tikai JSON."
    )
    for attempt in range(retries + 1):
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.5,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content or "{}"
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        new_body = (data.get("body") or "").strip()
        if not new_body:
            continue
        new_n = count_words(new_body)
        new_paragraphs = new_body.count("\n\n") + 1
        # Last-attempt leniency: accept 128+ if still short.
        low = 128 if attempt == retries else target_low
        high = target_high + 10
        if not (low <= new_n <= high):
            print(
                f"    retry {attempt + 1}: got {new_n} words, want {low}-{high}",
                file=sys.stderr,
                flush=True,
            )
            continue
        if abs(new_paragraphs - old_paragraphs) > 1:
            print(
                f"    retry {attempt + 1}: paragraphs {new_paragraphs} vs orig {old_paragraphs}",
                file=sys.stderr,
                flush=True,
            )
            continue
        return new_body
    return None


def main() -> int:
    load_env()
    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        print("XAI_API_KEY missing", file=sys.stderr)
        return 1
    model = os.environ.get("XAI_MODEL", "grok-4-1-fast")
    client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")

    topics, texts = load_catalog()
    failed: list[str] = []
    changed = 0
    t_start = time.time()

    non_seed = [t for t in texts if not is_seed(t)]
    print(f"Expanding {len(non_seed)} texts (skipping {len(texts) - len(non_seed)} seeds)...")
    print()

    for i, t in enumerate(texts):
        if is_seed(t):
            continue
        idx = sum(1 for x in texts[: i + 1] if not is_seed(x))
        old_n = count_words(t["body"])
        print(f"[{idx}/{len(non_seed)}] {t['id']:30s} {old_n:3d}w → ", end="", flush=True)
        start = time.time()
        new_body = expand_one(client, model, t)
        dur = time.time() - start
        if not new_body:
            print(f"FAIL ({dur:.1f}s)", flush=True)
            failed.append(t["id"])
            continue
        new_n = count_words(new_body)
        print(f"{new_n:3d}w (+{new_n - old_n}, {dur:.1f}s)", flush=True)
        t["body"] = new_body
        changed += 1

    save_catalog(topics, texts)
    print()
    print(f"Expanded {changed} / {len(non_seed)} texts in {time.time() - t_start:.1f}s.")
    if failed:
        print(f"FAILED ({len(failed)}): {failed}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
