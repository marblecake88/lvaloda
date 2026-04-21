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
    oficiālajam paraugam (PUTNI ZIEMĀ).

    STINGRAS PRASĪBAS KATRAM TEKSTAM:
    - 110–140 vārdi kopā (neskaiti virsrakstu).
    - 3 vai 4 rindkopas, atdalītas ar tukšu rindu.
    - Neitrāls, publicistisks stils — NEVIS dialogs, NEVIS stāsts pirmajā
      personā, NEVIS mākslinieciska proza. Tekstam jāizklausās kā raksts no
      ikdienas preses vai informatīvas brošūras.
    - Leksika — A2–B1 (bieži lietojama ikdienas un oficiālā leksika).
    - Saturs: konkrēts temats, fakti + praktiski padomi + eksperta viedoklis
      (piem., ornitologi, ārsti, speciālisti, vietējie iedzīvotāji) + sociāla
      vai vides dimensija.
    - Jāiekļauj vismaz viens skaitlis, viens salīdzinājums vai viens konkrēts
      piemērs (Rīga, Latvijā, oktobrī utml.).
    - Bez emojiem, bez zvaigznītēm, bez Markdown.
    - Virsraksts — VIENS vārds vai īsa frāze LIELIEM BURTIEM, bez pieturzīmēm.

    JAUTĀJUMI (vienmēr tieši 5):
    - Tie ir mutiski jautājumi, uz kuriem students atbild skatoties uz tekstu.
    - Pieci dažādi tipi: 1) fakts (Kas? Ko? Kur? Kad? Cik?), 2) iemesls
      (Kāpēc?), 3) veids (Kā? Kādā veidā?), 4) detaļa (Kurš? Kāds? No kā?),
      5) paplašinājums ar teksta informāciju (Ko vēl? Ko nedrīkst? Ko iesaka?).
    - Atbildi uz katru jautājumu var atrast tekstā — NEVAJAG jautāt par to,
      ko students domā pats no sevis.
    - Jautājums 1–2 teikumi, bez iesākumiem «Lūdzu» vai «Pasakiet».

    ATBILDES FORMĀTS — STRIKTI JSON (bez Markdown, bez komentāriem):
    {"texts":[{"id":"slug","title_lv":"NOSAUKUMS","topic":"topic_slug",
    "body":"1. rindkopa.\\n\\n2. rindkopa.\\n\\n3. rindkopa.\\n\\n4. rindkopa.",
    "questions":["1?","2?","3?","4?","5?"]}, ...]}

    «topic» vienmēr no dotā saraksta. «id» — īss angļu slug ar pasvītrojumiem
    (piem., "janu_svetki"). Garumzīmes ō, ā, ē, ī, ū, č, š, ž, ķ, ļ, ņ, ģ —
    obligātas tur, kur tās nepieciešamas.
    """
).strip()


def build_user_prompt(batch: list[tuple[str, str]]) -> str:
    lines = []
    lines.append("Uzraksti šos tekstus (šajā partijā {n} gab.):".format(n=len(batch)))
    for i, (topic_slug, subtopic) in enumerate(batch, 1):
        topic_full = TOPICS[topic_slug]
        lines.append(f"{i}. topic={topic_slug} ({topic_full}). Apakštēma: {subtopic}")
    lines.append("")
    lines.append("OFICIĀLIE PARAUGI (rakstī tieši tādā stilā un garumā):")
    for seed in SEED_TEXTS:
        lines.append("")
        lines.append(f"NOSAUKUMS: {seed['title_lv']}")
        lines.append(seed["body"])
        lines.append("")
        lines.append("JAUTĀJUMI:")
        for q in seed["questions"]:
            lines.append(f"- {q}")
    lines.append("")
    lines.append("Atgriez visu partiju vienā JSON objektā ar atslēgu \"texts\".")
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


def generate_batch(client: OpenAI, model: str, batch: list[tuple[str, str]]) -> list[dict[str, Any]]:
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(batch)},
        ],
        temperature=0.9,
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content or "{}"
    data = json.loads(raw)
    texts = data.get("texts", [])
    if not isinstance(texts, list):
        raise ValueError(f"Expected list under 'texts', got: {type(texts).__name__}")
    return texts


def main() -> int:
    load_env()
    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        print("ERROR: XAI_API_KEY not set", file=sys.stderr)
        return 1
    model = os.environ.get("XAI_MODEL", "grok-4-1-fast")
    client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")

    # Flatten subtopics into batches of 10
    all_pairs: list[tuple[str, str]] = []
    for topic_slug, subs in SUBTOPICS.items():
        for sub in subs:
            all_pairs.append((topic_slug, sub))
    batch_size = 10
    batches = [all_pairs[i:i + batch_size] for i in range(0, len(all_pairs), batch_size)]

    all_texts: list[dict[str, Any]] = list(SEED_TEXTS)
    for i, batch in enumerate(batches, 1):
        print(f"[{i}/{len(batches)}] generating {len(batch)} texts...", flush=True)
        start = time.time()
        try:
            texts = generate_batch(client, model, batch)
        except Exception as e:
            print(f"  batch {i} failed: {e}", file=sys.stderr)
            return 2
        dur = time.time() - start
        print(f"  got {len(texts)} in {dur:.1f}s", flush=True)
        # Normalize: ensure every entry has required keys, drop if not
        for t in texts:
            if all(k in t for k in ("id", "title_lv", "topic", "body", "questions")):
                if len(t["questions"]) == 5 and t["topic"] in TOPICS:
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
