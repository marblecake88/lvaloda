"""Generate the Lasīšana text catalog via Grok.

One-shot script. Reads XAI_API_KEY from the environment (load .env by hand
beforehand or run via `source ../.env && python generate_reading_texts.py`).
Writes backend/app/assets/reading_texts.py as a static Python catalog.

Format per text matches the official PMLP paraugs (PUTNI ZIEMĀ):
~130 words, 3-4 paragraphs, neutral-publicistic style, 5 questions of
varying types (fact, reason, manner, detail, extension/opinion).
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import textwrap
import time
from typing import Any

from openai import OpenAI

OUT_PATH = pathlib.Path(__file__).resolve().parents[1] / "backend/app/assets/reading_texts.py"

# Official PMLP paraugi — shipped verbatim so the catalog has at least
# two real exam artefacts. All others are Grok-generated in the same mold.
SEED_TEXTS: list[dict[str, Any]] = [
    {
        "id": "putni_ziema",
        "title_lv": "PUTNI ZIEMĀ",
        "topic": "laiks",
        "source": "PMLP paraugs (Latvieši un līvi)",
        "body": (
            "Kad pienāk ziema un kļūst auksti, cilvēki sāk barot putnus. Vieniem liekas, "
            "ka putniem nav ko ēst, citiem patīk tos vērot, vēl citi grib saviem bērniem "
            "parādīt dažādus putnus. Ja tos baro ziemā, putni labprāt pie mājām dzīvos "
            "arī vasarā, kad gaisā būs daudz mušu un kukaiņu.\n\n"
            "Mūsdienās var nopirkt gatavas barotavas, barības maisījumus, dažādus "
            "interjera priekšmetus putniem. Latvijā “modē” ir paštaisītās barotavas: "
            "no koka, piena pakām, plastmasas un stikla pudelēm, pat no konservu kārbām.\n\n"
            "Putnus barot ir jāsāk jau oktobrī, jo tad viņi sāk meklēt vietas, kur ziemā "
            "būs ēdiens. Cilvēkam jāatceras: ja viņš sāk barot putnus, tas ir jādara "
            "regulāri katru dienu. Putniem nedrīkst dot sālītu ēdienu un baltmaizi, "
            "vislabāk – dažādas sēklas, graudus, speķi.\n\n"
            "Ornitologi uzskata, ka nav pareizi barot putnus citos gadalaikos. Labāk ir "
            "radīt vidi, lai putni gribētu uzturēties tuvāk cilvēku mājām, piemēram, "
            "stādīt augļu kokus un ogu krūmus, būvēt putnu būrus."
        ),
        "questions": [
            "Kāpēc cilvēki ziemā baro putnus?",
            "No kāda materiāla izgatavo barotavas putniem Latvijā?",
            "Cik bieži ir jābaro putni ziemā?",
            "Kurš ēdiens ziemā ir vislabākais putniem?",
            "Ko vēl vajadzētu darīt, lai putni gribētu dzīvot tuvāk cilvēku mājām?",
        ],
    },
    {
        "id": "citrons",
        "title_lv": "CITRONS",
        "topic": "edieni",
        "source": "PMLP paraugs (Latvieši un līvi)",
        "body": (
            "Citrons vienlīdz labi iederas atspirdzinošā limonādē ar ledu un karstā "
            "tējā ar medu. Īstā limonāde: izspiež vienu ēdamkaroti citronu sulas, "
            "pievieno ēdamkaroti cukura, glāzi ūdens un sajauc.\n\n"
            "Par citronkoku dzimteni pētnieki vienbalsīgi atzīst Āziju. Reģionos, "
            "kur citroni aug, tos plaši lieto gan tautas medicīnā, gan pārtikā. "
            "Iespējams, ka pirmie svešzemnieki, kas novērtēja citronu labās "
            "īpašības, bija jūrasbraucēji – viņi ievēroja, ka citronu sula glābj no "
            "cingas, kas rodas ilgā kuģojumā, kad jāiztiek ar stipri vienveidīgu pārtiku.\n\n"
            "Citrons joprojām ir tāds kā etalons, ar kuru salīdzina citus C vitamīna "
            "avotus. Lai kur citroni nonāca, tie tika novērtēti un iecienīti. Tropu "
            "un subtropu zemēs cilvēki tos sāka audzēt dārzos, bet vēsākā klimatā "
            "centās padarīt par telpaugiem."
        ),
        "questions": [
            "Kā citronus izmanto vietas, kur tie aug?",
            "Kas jāpievieno ūdenim, lai pagatavotu īstu limonādi?",
            "Kādiem dzērieniem var pievienot citronu?",
            "No kurienes citrons izplatījās visā pasaulē?",
            "Kur cilvēki audzē citronkokus?",
        ],
    },
]

# 11 topic slots from the PMLP latviesilivi_1_0.docx.
TOPICS = {
    "gimene": "es un mani tuvinieki (ģimene, radi, draugi)",
    "dzivesvieta": "dzīves apstākļi un vide (māja, dzīvoklis, lauki, pilsēta)",
    "darbs": "izglītība, darbs, intereses",
    "attiecibas": "attiecības ar citiem cilvēkiem, pieklājība, kaimiņi",
    "kultura": "kultūra un sociālās lietas (tradīcijas, mūzika, teātris, kino)",
    "brivais_laiks": "brīvais laiks un sabiedriskā dzīve",
    "sports": "sports, vaļasprieks",
    "iepirksanas": "iepirkšanās, veikali, tirgus",
    "edieni": "ēdieni un dzērieni",
    "celosana": "ceļošana, Latvijas vietas, transports",
    "laiks": "laika apstākļi, gadalaiki, daba",
}

# Seed subtopics — a mix of uniquely Latvian angles and everyday life.
# Script generates 5 texts per topic → 55 generated + 1 seed = 56 total.
SUBTOPICS: dict[str, list[str]] = {
    "gimene": [
        "Jāņu svinēšana ģimenē",
        "Vecvecāku loma Latvijas ģimenēs",
        "Bērnu dzimšanas dienas",
        "Ģimenes vakariņas nedēļas nogalē",
        "Kāzu tradīcijas Latvijā",
    ],
    "dzivesvieta": [
        "Dzīve daudzdzīvokļu namā",
        "Lauku māja un piemājas dārzs",
        "Dzīvokļa īre Rīgā",
        "Vasarnīcas Latvijā",
        "Dzīvošana mikrorajonā",
    ],
    "darbs": [
        "Attālinātais darbs Latvijā",
        "Skolēnu vasaras darbi",
        "Pārkvalifikācija pieaugušajiem",
        "Populāras profesijas jauniešu vidū",
        "Rokdarbi kā hobijs",
    ],
    "attiecibas": [
        "Kaimiņattiecības daudzdzīvokļu mājā",
        "Kā latvieši iepazīstas",
        "Dāvanu pasniegšanas tradīcijas",
        "Palīdzība draugiem grūtā brīdī",
        "Pieklājības frāzes ikdienā",
    ],
    "kultura": [
        "Dziesmu un deju svētki",
        "Latvijas mūzikas skatuve",
        "Teātra apmeklēšana",
        "Latvijas muzeji",
        "Latviešu kino mūsdienās",
    ],
    "brivais_laiks": [
        "Pirts tradīcija Latvijā",
        "Makšķerēšana vasarā",
        "Pastaigas mežā",
        "Brīvprātīgais darbs",
        "Grāmatu lasīšana vakaros",
    ],
    "sports": [
        "Hokejs Latvijā",
        "Skriešana kā vaļasprieks",
        "Sēņu lasīšana rudenī",
        "Dārzkopība kā atpūta",
        "Dabas fotografēšana",
    ],
    "iepirksanas": [
        "Centrāltirgus Rīgā",
        "Iepirkšanās internetā",
        "Lauku zemnieku tirdziņi",
        "Lietoto preču veikali",
        "Latvijas maizes veikals",
    ],
    "edieni": [
        "Ziemassvētku galds",
        "Skābi kāposti ziemā",
        "Dzērvenes un to izmantošana",
        "Latviešu rudzu maize",
        "Tēja no dārza zālītēm",
    ],
    "celosana": [
        "Braukšana uz Lietuvu un Igauniju",
        "Jūrmala vasarā",
        "Ceļošana pa Latviju ar velosipēdu",
        "Lidojumi no Rīgas lidostas",
        "Atpūta Kurzemes piekrastē",
    ],
    "laiks": [
        "Latviešu rudens",
        "Sniegotas ziemas",
        "Baltās naktis jūnijā",
        "Rudens vēji un lietus",
        "Pavasara atmoda dabā",
    ],
}


SYSTEM_PROMPT = textwrap.dedent(
    """
    Tu esi autors mācību tekstiem latviešu valodas eksāmenam PMLP programmai
    «Latvieši un līvi» — pirmajai daļai «Lasīšana». Tavs uzdevums ir rakstīt
    īsus informatīvi-publicistiskus tekstus latviski, kas pilnībā atbilst
    oficiālajiem PMLP paraugiem (PUTNI ZIEMĀ, CITRONS).

    GARUMS — KRITISKI SVARĪGI:
    - 130–155 vārdi kopā (mērķis apm. 140). NEPIEŅEMAMS ir īsāks teksts.
    - 3 vai 4 rindkopas, atdalītas ar tukšu rindu (\\n\\n).
    - Katra rindkopa — 35–50 vārdi.

    STILS — KRITISKI SVARĪGI:
    - Neitrāls informatīvi-publicistisks stils — kā raksts no žurnāla vai
      informatīvas brošūras.
    - NEVIS dialogs, NEVIS stāsts pirmajā personā ("es domāju..."),
      NEVIS mākslinieciska proza, NEVIS reklāma, NEVIS mācību grāmatas stils.
    - Leksika — A2–B1 (bieži lietojama ikdienas un oficiālā leksika).
    - Teksta saturs: vispārējs temata ievads → praktiska informācija /
      padomi / fakti → eksperta viedoklis vai vispārināts secinājums.
    - Vismaz viens skaitlis / datums / konkrēts piemērs (Rīgā, Latvijā,
      oktobrī, pēdējos 10 gados, aptuveni 60 % utml.).
    - Vismaz viens eksperta balss (ornitologi / ārsti / speciālisti /
      vietējie iedzīvotāji / pētnieki).
    - Virsraksts — VIENS vārds vai īsa frāze LIELIEM BURTIEM, bez
      pieturzīmēm.

    VALODAS PAREIZĪBA — KRITISKI SVARĪGI:
    - Visas garumzīmes (ā, ē, ī, ū) un mīkstinājumzīmes (ķ, ļ, ņ, ģ) —
      obligāti tur, kur tās pēc pareizrakstības noteikumiem nepieciešamas.
    - Pareizi locījumi: lokatīvs ("Rīgā", nevis "Rīga"), ģenitīvs ("trīs
      bērnu", nevis "trīs bērni"), akuzatīvs utt.
    - Pareizas pēdiņas: „..." vai "..." (NEVIS neitralās " ").
    - Bez kalkām no krievu/angļu ("izmantot iespēju" nepareizi nāk no
      krievu "использовать возможность" — vietā izmanto "izmantot kādu
      iespēju" vai "gūt iespēju").
    - Bez anglicismiem un jaunloģismiem.
    - Bez emojiem, bez Markdown, bez zvaigznītēm.

    JAUTĀJUMI — VIENMĒR TIEŠI 5:
    - Tie ir mutiski jautājumi, uz kuriem students atbild, SKATOTIES
      TEKSTU. Katram jautājumam atbilde OBLIGĀTI IR ATRODAMA tekstā.
    - 5 DAŽĀDI tipi (ne divi vienādi):
      1) FAKTS (Kas? Ko? Kur? Kad? Cik?)
      2) IEMESLS / NOLŪKS (Kāpēc? Kādēļ? Kāda iemesla dēļ?)
      3) VEIDS / PROCESS (Kā? Kādā veidā? Ko dara...?)
      4) DETAĻA / KVALITĀTE (Kurš? Kāds? No kā?)
      5) PAPLAŠINĀJUMS ar teksta informāciju (Ko iesaka? Ko nedrīkst?
         Ko arī var darīt? Kādi vēl...?)
    - Jautājums īss: 1 teikums, bez iesākumiem «Lūdzu» vai «Pasakiet».

    ATBILDES FORMĀTS — STRIKTI JSON (bez Markdown, bez ``` blokiem, bez
    komentāriem):
    {"texts":[{"id":"slug","title_lv":"NOSAUKUMS","topic":"topic_slug",
    "body":"1. rindkopa.\\n\\n2. rindkopa.\\n\\n3. rindkopa.\\n\\n4. rindkopa.",
    "questions":["1?","2?","3?","4?","5?"]}, ...]}

    «topic» — tieši viens no dotā saraksta. «id» — īss angļu slug ar
    pasvītrojumiem (piem., "janu_svetki", "velosipeds_latvija").
    """
).strip()


def build_user_prompt(topic_slug: str, subtopic: str) -> str:
    topic_full = TOPICS[topic_slug]
    # Only the long seed in the prompt — the short one anchors the model too low.
    ref = SEED_TEXTS[0]
    ref_wc = len(ref["body"].split())
    lines = []
    lines.append("Uzraksti VIENU tekstu:")
    lines.append(f"- topic = {topic_slug} ({topic_full})")
    lines.append(f"- apakštēma = {subtopic}")
    lines.append("")
    lines.append("STINGRA STRUKTŪRA — rakstī TIEŠI 4 rindkopas šādā kārtībā:")
    lines.append("  1) IEVADS (40-45 vārdi): par ko būs teksts, kāpēc tas aktuāli,")
    lines.append("     ar kādu emocionālo vai sociālo kontekstu tas saistās Latvijā.")
    lines.append("  2) FAKTI (40-45 vārdi): konkrēti skaitļi, datumi, vietu nosaukumi,")
    lines.append("     piemēri no ikdienas (piem., 'pēdējos 10 gados', 'aptuveni 60 %',")
    lines.append("     'Rīgā', 'oktobrī', 'Centrāltirgū').")
    lines.append("  3) DETAĻAS UN PADOMI (40-45 vārdi): kā tas notiek praksē,")
    lines.append("     ko cilvēki dara, ko iesaka / ko nedrīkst, tipiskas situācijas.")
    lines.append("  4) SECINĀJUMS / EKSPERTA VIEDOKLIS (30-35 vārdi): ko iesaka")
    lieks = (
        "     speciālisti (ornitologi, ārsti, sociologi, vēsturnieki utml.);"
        " vispārināts secinājums par tēmu."
    )
    lines.append(lieks)
    lines.append("")
    lines.append("KOPĀ: 150-170 vārdi. Ja pēc sākuma melnrakstа sanāk īsāks par")
    lines.append("145 vārdiem — izvērs katru rindkopu, līdz sasniedz vismaz 145.")
    lines.append("")
    lines.append(f"OFICIĀLS PARAUGS no PMLP ({ref_wc} vārdi — tādā stilā):")
    lines.append("")
    lines.append(f"NOSAUKUMS: {ref['title_lv']}")
    lines.append(ref["body"])
    lines.append("")
    lines.append("JAUTĀJUMI:")
    for q in ref["questions"]:
        lines.append(f"- {q}")
    lines.append("")
    lines.append(
        'Atgriez JSON: {"texts":[{"id":"slug","title_lv":"NOSAUKUMS",'
        '"topic":"topic_slug","body":"...","questions":["1?","2?","3?","4?","5?"]}]}'
    )
    return "\n".join(lines)


def load_env() -> None:
    env_path = pathlib.Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k, v)


def _count_words(s: str) -> int:
    return len([w for w in s.split() if w])


def generate_one(
    client: OpenAI, model: str, topic_slug: str, subtopic: str, retries: int = 4
) -> dict[str, Any] | None:
    """Keep regenerating until length + paragraph structure pass. On the final
    attempt we relax the floor to 130 so a stubbornly short text still lands."""
    best_fallback: dict[str, Any] | None = None
    for attempt in range(retries + 1):
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(topic_slug, subtopic)},
            ],
            temperature=1.0,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content or "{}"
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        arr = data.get("texts") or []
        if not isinstance(arr, list) or not arr:
            continue
        t = arr[0]
        if not all(k in t for k in ("id", "title_lv", "topic", "body", "questions")):
            continue
        if len(t["questions"]) != 5 or t["topic"] not in TOPICS:
            continue
        n = _count_words(t["body"])
        paragraphs = t["body"].count("\n\n") + 1
        if paragraphs < 3 or paragraphs > 5:
            print(
                f"    retry {attempt + 1}: paragraphs={paragraphs}",
                file=sys.stderr, flush=True,
            )
            continue
        # Track the longest draft so we can fall back on it if retries exhaust.
        if best_fallback is None or n > _count_words(best_fallback["body"]):
            best_fallback = t
        if 135 <= n <= 170:
            return t
        print(
            f"    retry {attempt + 1}: got {n} words (want 135-170)",
            file=sys.stderr, flush=True,
        )
    # All retries failed — accept the longest draft we saw if it's at least 128.
    if best_fallback is not None and _count_words(best_fallback["body"]) >= 128:
        print(
            f"    fallback: accepting {_count_words(best_fallback['body'])}-word draft",
            file=sys.stderr, flush=True,
        )
        return best_fallback
    return None


def main() -> int:
    load_env()
    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        print("ERROR: XAI_API_KEY not set", file=sys.stderr)
        return 1
    model = os.environ.get("XAI_MODEL", "grok-4-1-fast")
    client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")

    all_pairs: list[tuple[str, str]] = []
    for topic_slug, subs in SUBTOPICS.items():
        for sub in subs:
            all_pairs.append((topic_slug, sub))

    all_texts: list[dict[str, Any]] = list(SEED_TEXTS)
    failed: list[str] = []
    for i, (topic_slug, sub) in enumerate(all_pairs, 1):
        print(f"[{i}/{len(all_pairs)}] {topic_slug:15s} {sub[:35]:35s} ", end="", flush=True)
        start = time.time()
        t = generate_one(client, model, topic_slug, sub)
        dur = time.time() - start
        if t is None:
            print(f"FAIL ({dur:.1f}s)", flush=True)
            failed.append(f"{topic_slug}:{sub}")
            continue
        n = _count_words(t["body"])
        print(f"{n}w ({dur:.1f}s)", flush=True)
        all_texts.append(t)

    # Deduplicate by id
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for t in all_texts:
        if t["id"] in seen:
            continue
        seen.add(t["id"])
        deduped.append(t)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    header = textwrap.dedent(
        '''
        """Lasīšana text catalog.

        Generated by scripts/generate_reading_texts.py. Two seed texts
        (PUTNI ZIEMĀ and CITRONS) are official PMLP paraugi for the
        «Latvieši un līvi» category; the rest are Grok-generated in the same
        mold (~130 words, 3-4 paragraphs, informative-publicistic style)
        across the 11 official PMLP topics.

        Format per entry:
        - id: short slug
        - title_lv: uppercase heading
        - topic: one of READING_TOPICS keys
        - source: "PMLP paraugs …" for seed, otherwise absent/synthetic
        - body: 3-4 paragraphs separated by "\\n\\n"
        - questions: exactly 5 Latvian questions of varying types
        """
        '''
    ).lstrip()
    topics_repr = json.dumps(TOPICS, ensure_ascii=False, indent=4)
    texts_repr = json.dumps(deduped, ensure_ascii=False, indent=4)
    OUT_PATH.write_text(
        header
        + "\nfrom __future__ import annotations\n\n"
        + "READING_TOPICS: dict[str, str] = "
        + topics_repr
        + "\n\nREADING_TEXTS: list[dict] = "
        + texts_repr
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {len(deduped)} texts to {OUT_PATH}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
