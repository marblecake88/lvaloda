# Lvaloda 🇱🇻

A personal Telegram Mini App for everyday spoken Latvian practice, built around
preparation for the Latvian oral language exam under the **«Latvieši un līvi»**
naturalisation programme (PMLP).

**Languages of this README:** [English](#english) · [Русский](#русский) · [Latviešu](#latviešu)

![Stack](https://img.shields.io/badge/python-3.12+-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-async-009688) ![React](https://img.shields.io/badge/React-18-61dafb) ![Vite](https://img.shields.io/badge/Vite-5-646cff) ![Telegram](https://img.shields.io/badge/Telegram-Mini%20App-26A5E4)

---

## English

### What it is

A self-hosted Telegram Mini App + bot for daily conversational Latvian practice.
Targeted at adult learners who already have an A1/A2 base and want to push
into confident A2-B1 spoken fluency — particularly for the PMLP oral exam.

The whole product is opinionated: **no grammar drills, no Anki SRS, no formal
textbook style**. The bot is told to speak natural everyday Rīga Latvian
("the way friends actually talk in 2025"), correct vocabulary gently, and
keep practice short and frequent.

### Features

- **Saruna** — open-ended dialogues across 6 daily situations (cafe, market,
  asking directions, phone call, neighbour small-talk, free chat). The bot
  flags unnatural phrases with `💡 Dabiskāk: ...` blocks (with brief Russian
  explanations). End-of-session analysis: fluency 1-5, "what could be more
  natural", new vocabulary, tips.
- **Eksāmena simulācija** — 13 PMLP-exam topics. Examiner-style deep
  conversation (~10-15 min), follow-up questions, no help during the
  session. Final structured report. **Anti-repeat** between sessions:
  covered "angles" of a topic are persisted; the next run on the same topic
  enters from new angles. When all standard angles are covered, the model
  escalates to hypotheticals and abstract opinions.
- **Top frāzes** — 11 categories × ~25-30 most-used everyday phrases (~290
  total): greetings, questions, reactions, feelings, verbs, home/people, food,
  numbers/time, transport/directions, adjective-noun collocations, useful
  conversational phrases. Per-session: 10 random cards, flashcard flip
  mechanic with `Zinu / Nezinu / Atpakaļ`. Per-category history of last 10
  runs.
- **Shadowing** — listen → record → compare. The bot generates 8 living
  conversational phrases for the chosen topic, each played back natively
  (TTS) at normal or 0.75× speed. Evidence-backed for accent and prosody.
- **Apraksti attēlu** — picture description with **Grok image generation**
  (`grok-imagine-image`). 15 themed scenes (cafe, kitchen, market, family
  dinner, classroom, doctor, train station, beach, gym, festival, library,
  …). Pictures are persisted long-term; you can browse history and re-open
  past pictures. End-of-session: Grok **vision** analyses your description
  vs the actual image, scores accuracy 1-5, lists what you missed, and
  produces a simple-language description as it should sound.
- **Tulkotājs** — RU ↔ LV translator with auto-language detection. Text or
  voice input. Output is natural conversational, with TTS playback.
- **Vārdnīca** — saved words + auto-collected mistakes (every `💡 Dabiskāk`
  block is logged). Tap 🔖 in chat to save. 🔊 plays each entry.
- **Statistika** — streak, today's minutes vs daily goal, 30-day calendar
  heatmap, topic coverage breakdown, weekly minutes.
- **Adaptive difficulty** — fluency_score from past exam runs is fed back
  into prompts; "known vocab" (your saved words) gets nudged into bot
  replies for spaced retrieval through real conversation, not flashcards.
- **CloudStorage resume** — closed the Mini App mid-session? On reopen,
  Home shows a "Turpināt?" banner.
- **Bot reminders** — `/remind 19:00` schedules a daily push with a topic
  suggestion (alternates exam-topic / daily situation). Voice messages to
  the bot work as a fallback chat.
- **Weekly summary** — every Monday 10:00 (Rīgas laiks) the bot DMs a
  Grok-generated review of the past week's practice.

### Stack

- **Backend:** Python 3.12+, FastAPI (async), aiogram 3, SQLAlchemy 2 +
  aiosqlite, APScheduler. Manage with `uv`.
- **Frontend:** React 18 + Vite + TypeScript + Telegram WebApp JS API.
- **LLM (text + vision):** xAI Grok (`grok-4-fast` for chat, `grok-imagine-image`
  for image generation). All text traffic goes through xAI's
  OpenAI-compatible endpoint at `https://api.x.ai/v1`.
- **STT / TTS:** OpenAI Whisper-1 + tts-1.

### Why these choices

- **xAI Grok over OpenAI for chat** — substantially cheaper, fluent in Latvian,
  vision works on the same endpoint.
- **OpenAI for STT/TTS** — Whisper handles Latvian noticeably better than
  alternatives; tts-1 voices read Latvian naturally.
- **SQLite, single-user-friendly** — zero ops, fast, fine for a personal app.

### First-time setup (local dev)

#### 1. API keys

- **Telegram Bot Token** — talk to [@BotFather](https://t.me/BotFather), `/newbot`
- **xAI API key** — https://console.x.ai/
- **OpenAI API key** — https://platform.openai.com/api-keys

#### 2. Env

```bash
cp .env.example .env
# Fill BOT_TOKEN, XAI_API_KEY, OPENAI_API_KEY.
# Leave WEBAPP_URL as-is for now — we'll set it after ngrok.
```

#### 3. Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 4. Frontend (separate terminal)

```bash
cd frontend
npm install
npm run dev   # listens on :5173
```

#### 5. ngrok (for the Telegram webhook + Mini App URL)

The Vite dev server already proxies `/api/*`, `/telegram/*`, and `/healthz` to
the backend, so you only need one ngrok pointing to `:5173`:

```bash
ngrok http 5173
```

Update `.env`:

```
WEBAPP_URL=https://xxxx.ngrok-free.app
```

Restart the backend — it will register the Telegram webhook to
`{WEBAPP_URL}/telegram/webhook` automatically on startup.

#### 6. Configure the Mini App in BotFather

```
/mybots → <your bot> → Bot Settings → Menu Button → Configure Menu Button
URL: https://xxxx.ngrok-free.app
Text: Parunāties
```

#### 7. Smoke test

1. Open the bot in Telegram → `/start` → tap the Mini App button.
2. Tap `Saruna` → pick `Kafejnīca / restorāns` → exchange a few messages →
   `Beigt` → see the analysis.
3. Tap `Top frāzes` → any category → flip cards → finish → see the run history.
4. Tap `Apraksti attēlu` → `↻` → pick a scene → describe → `Beigt` → see
   the vision-based report.
5. `/remind 19:00` to bot → confirms the daily reminder.

### Project layout

```
backend/app/
  config.py            # pydantic-settings from .env
  main.py              # FastAPI app + aiogram webhook + scheduler bootstrap
  db/                  # SQLAlchemy models, async session
  auth/telegram.py     # initData HMAC verification
  llm/
    client.py          # AsyncOpenAI clients (Grok + OpenAI)
    scenarios.py       # scenario catalog
    prompts.py         # system prompts (dialog, exam, analysis, picture)
    chat.py            # dialog_reply, exam_reply, analyze_*, russian_hint
    audio.py           # Whisper STT (with Cyrillic-detection retry), TTS
  services/            # stats, retrieval, unnatural-phrase extraction
  api/                 # FastAPI routers (chat, exam, picture, phrases, …)
  bot/
    handlers.py        # /start, /remind, voice fallback
    scheduler.py       # daily reminders + weekly summary
  assets/
    minimal_pairs.py   # curated phonetic contrasts
    pictures.py        # picture-mode scene catalog + Grok image gen
    top_phrases.py     # 290-phrase catalog across 11 categories
frontend/src/
  App.tsx              # routes
  api.ts, tg.ts        # backend client + Telegram WebApp helpers
  cloud.ts             # CloudStorage wrapper for resume
  hooks/useRecorder.ts # MediaRecorder + level meter + cancel
  components/          # InputBar, SaveWordSheet
  screens/             # Home, Chat, Exam, Picture, Phrases, …
```

### Deploying to your own host

1. Run the backend as a long-lived process (systemd / docker / tmux). Use a
   persistent volume for `lvaloda.db` and the generated-picture cache.
2. Build the frontend (`npm run build`) and serve `frontend/dist/` via nginx
   (or via FastAPI `StaticFiles` if you prefer one process).
3. nginx with HTTPS (Let's Encrypt) reverse-proxies `/api/*` and
   `/telegram/webhook` to the backend.
4. In BotFather, set the Mini App URL to your domain.
5. Set `WEBAPP_URL=https://your.domain.tld` in `.env`.

### Cost estimate

For a single user practising ~30 min/day:

| Service | Approx. monthly |
|---|---|
| xAI Grok (`grok-4-fast`) chat | $3–5 |
| xAI image gen (`grok-imagine-image`) | $0.50–1.50 |
| OpenAI Whisper STT | $5–6 |
| OpenAI TTS (on-demand) | $1–2 |
| **Total** | **~$10–14 / month** |

### Licence

MIT.

---

## Русский

### Что это

Self-hosted Telegram Mini App + бот для ежедневной разговорной практики
латышского. Целится во взрослых учеников с базой A1/A2, которые хотят
добраться до уверенного разговорного A2-B1 — в частности, к устному
экзамену PMLP по программе **«Latvieši un līvi»**.

Принципы:
- **Никакой грамматической задротни, никакого Anki, никакого учебникового
  стиля.** Боту явно сказано говорить как живой человек в Риге 2025
  («как реально друзья общаются»), мягко поправлять лексику, держать
  сессии короткими и регулярными.

### Фичи

- **Saruna** — свободные диалоги по 6 бытовым ситуациям. Бот мягко
  отмечает неестественные фразы блоком `💡 Dabiskāk: ...` с краткой
  русской подсказкой. В конце сессии — разбор: беглость 1-5, что было
  неестественно, новая лексика, советы.
- **Eksāmena simulācija** — 13 экзаменационных тем PMLP. Глубокая беседа
  на 10-15 мин с follow-up вопросами, без подсказок во время сессии.
  Финальный structured report. **Анти-повтор**: «углы» темы (под-аспекты)
  сохраняются, следующий заход на ту же тему заходит с других сторон.
  Когда стандартные углы исчерпаны — бот усложняет (гипотетика, абстрактные
  мнения).
- **Top frāzes** — 11 тем × ~25-30 самых частых фраз (≈290): приветствия,
  вопросы, реакции, чувства, глаголы, дом/люди, еда, числа/время,
  транспорт/направления, прилагательные с существительными, полезные фразы.
  За сессию — 10 случайных карточек, flashcard-флип `Zinu / Nezinu / Atpakaļ`.
  По каждой теме — история последних 10 заходов.
- **Shadowing** — слушай → повтори → сравни. Бот генерит 8 живых
  разговорных фраз по теме, проигрывает их через TTS на обычной или
  0.75× скорости.
- **Apraksti attēlu** — описание картинок с **генерацией через Grok**
  (`grok-imagine-image`). 15 тематических сцен. Картинки сохраняются
  надолго, можно листать историю и переоткрыть прошлые. В конце — Grok
  **vision** сравнивает твоё описание с реальной картинкой, ставит
  точность 1-5, перечисляет что пропустил, выдаёт простое описание
  «как должно звучать».
- **Tulkotājs** — RU ↔ LV переводчик с автоопределением языка. Текст или
  голос. Перевод — живой разговорный, есть TTS.
- **Vārdnīca** — сохранённые слова + автоматически собираемые ошибки.
  Тап 🔖 в чате — сохранить слово. 🔊 — послушать.
- **Statistika** — стрик, минуты сегодня vs дневная цель, тепловой
  календарь за 30 дней, разбивка по темам.
- **Адаптивная сложность** — средний fluency_score из прошлых экзаменов
  попадает в промпты; «знакомая лексика» (сохранённые слова) аккуратно
  вплетается ботом в реплики — spaced retrieval через реальный диалог.
- **CloudStorage resume** — закрыл мини-апп? На главном — баннер
  «Turpināt?».
- **Напоминания бота** — `/remind 19:00` ставит ежедневный пуш с темой
  дня. Голосовухи в личку боту работают как fallback-чат.
- **Weekly summary** — каждый понедельник в 10:00 (Rīgas laiks) бот
  присылает сводку прошлой недели, сгенерированную Grok'ом.

### Стек

- **Backend:** Python 3.12+, FastAPI, aiogram 3, SQLAlchemy 2 + aiosqlite,
  APScheduler. Менеджер пакетов — `uv`.
- **Frontend:** React 18 + Vite + TypeScript + Telegram WebApp JS API.
- **LLM:** xAI Grok (`grok-4-fast` чат + `grok-imagine-image` картинки)
  через OpenAI-совместимый endpoint `https://api.x.ai/v1`.
- **STT / TTS:** OpenAI Whisper-1 + tts-1.

### Первый запуск (локально)

#### 1. Получить ключи

- **Telegram Bot Token** — [@BotFather](https://t.me/BotFather), `/newbot`
- **xAI API key** — https://console.x.ai/
- **OpenAI API key** — https://platform.openai.com/api-keys

#### 2. Env

```bash
cp .env.example .env
# Заполнить BOT_TOKEN, XAI_API_KEY, OPENAI_API_KEY.
# WEBAPP_URL пока не трогать — обновим после ngrok.
```

#### 3. Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 4. Frontend (другой терминал)

```bash
cd frontend
npm install
npm run dev   # на :5173
```

#### 5. ngrok

Vite dev-server уже проксирует `/api/*`, `/telegram/*`, `/healthz` на бэк —
достаточно одного ngrok на `:5173`:

```bash
ngrok http 5173
```

Обновить `.env`:

```
WEBAPP_URL=https://xxxx.ngrok-free.app
```

Перезапустить бэк — он сам зарегистрирует webhook на
`{WEBAPP_URL}/telegram/webhook`.

#### 6. Настроить Mini App в BotFather

```
/mybots → <your bot> → Bot Settings → Menu Button
URL: https://xxxx.ngrok-free.app
Text: Parunāties
```

#### 7. Smoke-тест

1. Открыть бота в Telegram → `/start` → тапнуть кнопку Mini App.
2. `Saruna` → `Kafejnīca / restorāns` → пара сообщений → `Beigt` → разбор.
3. `Top frāzes` → любая категория → пройти 10 карточек → история заходов.
4. `Apraksti attēlu` → `↻` → выбрать сцену → описать → `Beigt` → vision-разбор.
5. `/remind 19:00` боту → подтверждение пуша.

### Структура

См. английскую секцию выше — пути и имена файлов те же.

### Деплой на свой хост

1. Бэк как долгоиграющий процесс (systemd / docker / tmux). Обязательно
   персистентный volume для `lvaloda.db` и кеша картинок.
2. Билд фронта (`npm run build`) → отдавать `frontend/dist/` через nginx,
   либо примонтировать `StaticFiles` в FastAPI и держать один процесс.
3. nginx с HTTPS (Let's Encrypt) → проксирует `/api/*` и `/telegram/webhook`
   на бэк.
4. В BotFather — Mini App URL на свой домен.
5. В `.env` — `WEBAPP_URL=https://your.domain.tld`.

### Бюджет

При ~30 мин/день одним пользователем:

| Сервис | Примерно в месяц |
|---|---|
| xAI Grok (`grok-4-fast`) чат | $3–5 |
| xAI image gen (`grok-imagine-image`) | $0.50–1.50 |
| OpenAI Whisper STT | $5–6 |
| OpenAI TTS | $1–2 |
| **Итого** | **~$10–14 / месяц** |

### Лицензия

MIT.

---

## Latviešu

### Kas tas ir

Pašhostēta Telegram Mini App + bots ikdienas latviešu sarunvalodas
praksei. Domāts pieaugušajiem ar A1/A2 līmeni, kuri vēlas sasniegt drošu
A2-B1 sarunu līmeni — īpaši PMLP **«Latvieši un līvi»** mutiskajam
eksāmenam.

Pamatprincipi:
- **Nekādu gramatikas urbumu, nekāda Anki, nekāda mācību grāmatas stila.**
  Botam ir skaidri pateikts runāt kā īsts cilvēks Rīgā 2025. gadā
  («tā, kā draugi reāli runā»), maigi labot vārdu krājumu, sesijas turēt
  īsas un regulāras.

### Funkcijas

- **Saruna** — brīvas sarunas 6 ikdienas situācijās (kafejnīca, tirgus,
  ceļa jautāšana, saruna pa telefonu, kaimiņu small-talk, brīvais čats).
  Bots maigi atzīmē nedabiskas frāzes ar `💡 Dabiskāk: ...` bloku (ar īsu
  paskaidrojumu krieviski). Sesijas beigās — atskaite: plūdums 1-5, kas
  bija nedabiski, jauna leksika, padomi.
- **Eksāmena simulācija** — 13 PMLP eksāmena tēmas. Dziļa saruna 10-15
  minūtes ar follow-up jautājumiem, bez padomiem sesijas laikā.
  Strukturēta gala atskaite. **Anti-atkārtojums** starp sesijām — tēmas
  «leņķi» (apskatītie aspekti) tiek saglabāti; nākamais mēģinājums uz to
  pašu tēmu sākas no jauniem leņķiem. Kad standarta leņķi izsmelti — bots
  pārslēdzas uz hipotētiku un abstraktiem viedokļiem.
- **Top frāzes** — 11 kategorijas × ~25-30 visbiežāk lietoto frāžu
  (~290 kopā): sveicieni, jautājumi, atbildes, jūtas, darbības vārdi,
  mājas/cilvēki, ēdiens, skaitļi/laiks, transports/virzieni,
  īpašības vārdi ar lietvārdiem, noderīgas sarunvalodas frāzes. Vienā
  sesijā — 10 nejauši izvēlētas kartes, flashcard-flip `Zinu / Nezinu /
  Atpakaļ`. Katrai kategorijai — pēdējo 10 mēģinājumu vēsture.
- **Shadowing** — klausies → atkārto → salīdzini. Bots ģenerē 8 dzīvas
  sarunvalodas frāzes par tēmu, atskaņo tās ar TTS parastā vai 0.75×
  ātrumā.
- **Apraksti attēlu** — attēla aprakstīšana ar **Grok ģenerāciju**
  (`grok-imagine-image`). 15 tematiskās ainas. Attēli tiek saglabāti
  ilgtermiņā, var pārlūkot vēsturi un atvērt iepriekšējos. Sesijas
  beigās — Grok **vision** salīdzina tavu aprakstu ar reālo attēlu,
  novērtē precizitāti 1-5, uzskaita, ko tu nepamanīji, un sniedz vienkāršu
  aprakstu, kā tam vajadzētu skanēt.
- **Tulkotājs** — RU ↔ LV ar valodas auto-noteikšanu. Teksts vai balss.
  Tulkojums — dzīvs sarunvalodas, ar TTS atskaņošanu.
- **Vārdnīca** — saglabātie vārdi + automātiski apkopotās kļūdas. Pieskaries
  🔖 čatā, lai saglabātu vārdu. 🔊 — noklausīties.
- **Statistika** — strīks, šodienas minūtes pret dienas mērķi, 30 dienu
  siltumkarte, tēmu sadalījums.
- **Adaptīva grūtība** — vidējais fluency_score no iepriekšējiem
  eksāmeniem nonāk promptos; «zināmā leksika» (saglabātie vārdi) tiek
  ieausta bota replikās — atkārtota saskarsme caur reālu sarunu, nevis
  kartēm.
- **CloudStorage atjaunošana** — aizvēri Mini App? Sākumā parādīsies
  «Turpināt?» banneris.
- **Bota atgādinājumi** — `/remind 19:00` iestata dienas push ar tēmas
  ieteikumu. Balss ziņas botam darbojas kā fallback-čats.
- **Nedēļas kopsavilkums** — katru pirmdienu plkst. 10:00 (Rīgas laikā)
  bots nosūta nedēļas atskaiti, ko ģenerē Grok.

### Tehnoloģiju steks

- **Backend:** Python 3.12+, FastAPI, aiogram 3, SQLAlchemy 2 + aiosqlite,
  APScheduler. Pakešu pārvaldnieks — `uv`.
- **Frontend:** React 18 + Vite + TypeScript + Telegram WebApp JS API.
- **LLM:** xAI Grok (`grok-4-fast` čats + `grok-imagine-image` attēli)
  caur OpenAI-saderīgo endpoint `https://api.x.ai/v1`.
- **STT / TTS:** OpenAI Whisper-1 + tts-1.

### Pirmā palaišana (lokāli)

#### 1. API atslēgas

- **Telegram Bot Token** — [@BotFather](https://t.me/BotFather), `/newbot`
- **xAI API key** — https://console.x.ai/
- **OpenAI API key** — https://platform.openai.com/api-keys

#### 2. Env

```bash
cp .env.example .env
# Aizpildīt BOT_TOKEN, XAI_API_KEY, OPENAI_API_KEY.
# WEBAPP_URL pagaidām neaiztiec — atjaunosim pēc ngrok.
```

#### 3. Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 4. Frontend (cits terminālis)

```bash
cd frontend
npm install
npm run dev   # uz :5173
```

#### 5. ngrok

Vite dev-serveris jau proksē `/api/*`, `/telegram/*`, `/healthz` uz
backend — pietiek ar vienu ngrok uz `:5173`:

```bash
ngrok http 5173
```

Atjaunot `.env`:

```
WEBAPP_URL=https://xxxx.ngrok-free.app
```

Pārstartē backend — tas pats reģistrēs webhook uz
`{WEBAPP_URL}/telegram/webhook`.

#### 6. Konfigurēt Mini App BotFather

```
/mybots → <your bot> → Bot Settings → Menu Button
URL: https://xxxx.ngrok-free.app
Text: Parunāties
```

#### 7. Pārbaude

1. Atver botu Telegram → `/start` → pieskaries Mini App pogai.
2. `Saruna` → `Kafejnīca / restorāns` → daži ziņojumi → `Beigt` → atskaite.
3. `Top frāzes` → jebkura kategorija → izej 10 kartes → vēsture.
4. `Apraksti attēlu` → `↻` → izvēlies ainu → apraksti → `Beigt` → vision-atskaite.
5. `/remind 19:00` botam → apstiprinājums.

### Projekta struktūra

Skaties angļu sadaļā augstāk — failu ceļi un nosaukumi tie paši.

### Izvietošana uz sava hosta

1. Backend kā ilglaika process (systemd / docker / tmux). Obligāti
   pastāvīgs volume priekš `lvaloda.db` un attēlu kešas.
2. Frontend bilds (`npm run build`) → atdod `frontend/dist/` caur nginx,
   vai pievienot `StaticFiles` FastAPI un turēt vienu procesu.
3. nginx ar HTTPS (Let's Encrypt) → proksē `/api/*` un `/telegram/webhook`
   uz backend.
4. BotFather — Mini App URL uz savu domēnu.
5. `.env` — `WEBAPP_URL=https://your.domain.tld`.

### Budžets

Vienam lietotājam ar ~30 min/dienā:

| Pakalpojums | Aptuveni mēnesī |
|---|---|
| xAI Grok (`grok-4-fast`) čats | $3–5 |
| xAI attēlu ģenerācija (`grok-imagine-image`) | $0.50–1.50 |
| OpenAI Whisper STT | $5–6 |
| OpenAI TTS | $1–2 |
| **Kopā** | **~$10–14 / mēnesī** |

### Licence

MIT.
