"""Pass 2 — proofread every reading text + its 5 questions.

Per-text, zero-temperature query to Grok acting as a native Latvian editor.
Returns:
  - corrected_body / corrected_questions
  - issues: list of {where, type, original, fix} — audit trail
  - confidence: 1-5

Apply rule: iff confidence >= 4 AND issues is non-empty, accept the
corrected version and record issues. Otherwise leave untouched. Seeds
(PUTNI ZIEMĀ, CITRONS) are also skipped — they are official paraugi.

Writes the catalog back in place and appends a sibling audit log
`reading_review.log.json` with all issues for manual review.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import time
from typing import Any

from openai import OpenAI

from _reading_io import (  # type: ignore[import-not-found]
    CATALOG_PATH,
    count_words,
    is_seed,
    load_catalog,
    load_env,
    save_catalog,
)


AUDIT_PATH = CATALOG_PATH.parent / "reading_review.log.json"


SYSTEM_PROMPT = """Tu esi profesionāls latviešu valodas redaktors un filologs, \
dzimtais latviešu valodas runātājs. Tev dots īss informatīvi-publicistisks \
teksts un 5 mutiski jautājumi par to (PMLP eksāmena paraugs, programma \
«Latvieši un līvi»). Teksts paredzēts A2-B1 eksaminētajiem.

PĀRBAUDI SEKOJOŠO:

1) ORTOGRĀFIJA
   - Garumzīmes: ā, ē, ī, ū visur, kur tās nepieciešamas.
   - Mīkstinājumzīmes: ķ, ļ, ņ, ģ.
   - š, č, ž rakstība.
   - Locījumu galotnes (-a, -as, -ai, -u, -ā u.c.).

2) GRAMATIKA
   - Lietvārda dzimtes un skaitļa saskaņošana ar darbības vārdu un īpašības vārdu.
   - Locījumu pareiza izvēle (nominatīvs / ģenitīvs / datīvs / akuzatīvs / lokatīvs u.c.).
   - Priedēkļi un galotnes pie darbības vārdiem.
   - Vārdu kārtība teikumā.

3) STILS
   - Nav kalku no angļu/krievu valodas (piem., "izmantot iespēju" nepieciešamības vietā).
   - Nav anglicismu vai jaunlokunvārdu.
   - Nav skolas/mācību grāmatas stila (formāli-sausa valoda).
   - Nav pārspīlētu konstrukciju.

4) PIETURZĪMES
   - Pareizas pēdiņas: "..." (nevis " " vai " ").
   - Defise/domuzīme (–) tur, kur vajag.
   - Komati saliktos teikumos.

5) JAUTĀJUMI (5 gab.)
   - Uz katru jautājumu eksaminējams var atbildēt, **skatoties uz tekstu** \
(atbilde jābūt atrodama vai skaidri izsecināma no teksta).
   - Gramatiski un stilistiski korekti formulēti.
   - 5 jautājumi aptver 5 dažādus tipus: fakts, iemesls, veids, detaļa, \
paplašinājums (viedoklis vai papildu informācija).
   - Ja divi jautājumi pārāk līdzīgi — nedaudz pārformulē vienu, saglabājot \
mērķi.

SVARĪGI:
- NEMAINI teksta galveno saturu un idejas.
- NEMAINI teksta garumu būtiski (±10%).
- Ja teksts un jautājumi ir nevainojami — atgriez tos PRECĪZI kā saņemtus \
ar `issues=[]` un `confidence=5`.
- Ja kļūdas ir — labo, un katrai kļūdai uzraksti vienu ierakstu `issues` \
masīvā.

ATBILDE — STINGRĀ JSON, bez Markdown, bez ``` blokiem:
{
  "corrected_body": "teksts ar oriģinālo skaitu rindkopu, atdalītām ar \\n\\n",
  "corrected_questions": ["Q1?", "Q2?", "Q3?", "Q4?", "Q5?"],
  "issues": [
    {"where": "body" | "q1" | "q2" | "q3" | "q4" | "q5",
     "type": "ortogrāfija" | "gramatika" | "stils" | "pieturzīmes" | "jautājums",
     "original": "kā bija oriģinālā",
     "fix": "kā izlabots un kāpēc (īsi)"}
  ],
  "confidence": <int 1-5, cik pārliecināts esi par galīgo versiju>
}
"""


def review_one(
    client: OpenAI, model: str, text: dict[str, Any]
) -> dict[str, Any] | None:
    user_msg = (
        f"NOSAUKUMS: {text['title_lv']}\n\n"
        f"TEKSTS:\n---\n{text['body']}\n---\n\n"
        f"JAUTĀJUMI:\n"
        + "\n".join(f"{i + 1}. {q}" for i, q in enumerate(text["questions"]))
        + "\n\nPārbaudi un atgriez JSON."
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    # shape check
    if not isinstance(data.get("corrected_body"), str):
        return None
    if not (
        isinstance(data.get("corrected_questions"), list)
        and len(data["corrected_questions"]) == 5
    ):
        return None
    data.setdefault("issues", [])
    data.setdefault("confidence", 3)
    return data


def main() -> int:
    load_env()
    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        print("XAI_API_KEY missing", file=sys.stderr)
        return 1
    model = os.environ.get("XAI_MODEL", "grok-4-1-fast")
    client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")

    topics, texts = load_catalog()
    non_seed = [t for t in texts if not is_seed(t)]
    print(f"Reviewing {len(non_seed)} texts (skipping {len(texts) - len(non_seed)} seeds)...")
    print()

    audit: list[dict[str, Any]] = []
    changed = 0
    rejected = 0
    failed: list[str] = []
    t_start = time.time()

    for i, t in enumerate(texts):
        if is_seed(t):
            continue
        idx = sum(1 for x in texts[: i + 1] if not is_seed(x))
        print(f"[{idx}/{len(non_seed)}] {t['id']:30s}", end=" ", flush=True)
        start = time.time()
        result = review_one(client, model, t)
        dur = time.time() - start
        if result is None:
            print(f"FAIL ({dur:.1f}s)", flush=True)
            failed.append(t["id"])
            continue
        conf = result.get("confidence", 3)
        issues = result.get("issues") or []
        print(
            f"conf={conf} issues={len(issues):2d} ({dur:.1f}s)",
            flush=True,
        )
        audit.append(
            {
                "id": t["id"],
                "confidence": conf,
                "issues": issues,
                "applied": False,
            }
        )
        # Apply only when the editor is confident AND flagged something.
        if conf >= 4 and issues:
            new_body = result["corrected_body"].strip()
            new_qs = [q.strip() for q in result["corrected_questions"]]
            # word-count sanity (±15%)
            old_n = count_words(t["body"])
            new_n = count_words(new_body)
            if not (old_n * 0.85 <= new_n <= old_n * 1.15):
                print(
                    f"    REJECT: word count {old_n}→{new_n} outside ±15%",
                    flush=True,
                )
                rejected += 1
                continue
            t["body"] = new_body
            t["questions"] = new_qs
            audit[-1]["applied"] = True
            changed += 1

    save_catalog(topics, texts)
    AUDIT_PATH.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print()
    print(f"Applied: {changed} / {len(non_seed)}")
    print(f"Rejected (bad word count): {rejected}")
    print(f"Failed (parse error): {len(failed)} {failed}")
    print(f"Audit log: {AUDIT_PATH}")
    print(f"Elapsed: {time.time() - t_start:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
