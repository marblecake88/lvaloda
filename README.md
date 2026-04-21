# Lvaloda 🇱🇻

Personal Telegram Mini App for everyday spoken Latvian practice — built around
preparation for the PMLP oral exam («Latvieši un līvi» naturalisation programme).

**Languages:** [English](#english) · [Русский](#русский) · [Latviešu](#latviešu)

![Stack](https://img.shields.io/badge/python-3.12+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688)
![React](https://img.shields.io/badge/React-18-61dafb)
![Vite](https://img.shields.io/badge/Vite-5-646cff)
![Docker](https://img.shields.io/badge/Docker-compose-2496ED)
![Telegram](https://img.shields.io/badge/Telegram-Mini%20App-26A5E4)

Production deployment: [`https://lvaloda.taras.marblecake.fun`](https://lvaloda.taras.marblecake.fun)

---

## English

### What it is

A self-hosted Telegram Mini App + bot for daily conversational Latvian
practice. For adult learners with an A1/A2 base who want confident A2-B1
spoken fluency — specifically for the PMLP oral exam.

Opinionated: **no grammar drills, no Anki, no textbook style.** The bot is
told to speak everyday Rīga Latvian ("the way friends actually talk in 2025"),
correct vocabulary gently, and keep practice short and frequent.

### Features

- **Saruna** — open-ended dialogues across 6 daily situations (cafe, market,
  directions, phone call, neighbour small-talk, free chat). Gently flags
  unnatural phrases with `💡 Dabiskāk: ...` blocks and brief Russian hints.
  End-of-session analysis: fluency 1-5, what could be more natural, new
  vocabulary, tips.
- **Eksāmena simulācija** — 13 PMLP-exam topics. Examiner-style
  conversation (~10-15 min), follow-up questions, no help during the session.
  Structured final report. **Anti-repeat** between sessions: covered "angles"
  of a topic are persisted; the next run enters from new angles, and when
  standard angles are exhausted the bot escalates to hypotheticals.
- **Top frāzes** — 11 categories × ~25-30 phrases (~290 total). 10 random
  flashcards per run, `Zinu / Nezinu / Atpakaļ` flip mechanic, per-category
  history of last 10 runs.
- **Shadowing** — listen → record → compare. 8 living conversational phrases
  per topic, TTS at normal or 0.75× speed.
- **Apraksti attēlu** — picture description with Grok image generation
  (`grok-imagine-image`) across 15 themed scenes. Pictures are persisted and
  browsable. Final report: Grok vision compares your description to the
  actual image, scores accuracy 1-5, lists what you missed, writes a
  simple-language model description.
- **Tulkotājs** — RU ↔ LV with auto language detection. Text or voice.
  Natural conversational output with TTS playback.
- **Vārdnīca** — saved words + auto-collected mistakes (every
  `💡 Dabiskāk` block is logged). Tap 🔖 in chat to save, 🔊 to hear.
- **Statistika** — streak, daily minutes vs. goal, 30-day heatmap, topic
  coverage breakdown, weekly minutes.
- **Adaptive difficulty** — past exam fluency_score feeds into prompts;
  known vocab (your saved words) gets nudged into bot replies for spaced
  retrieval through real conversation.
- **CloudStorage resume** — closed the Mini App mid-session? Home shows a
  "Turpināt?" banner.
- **Bot reminders** — `/remind 19:00` schedules a daily push with a topic
  suggestion. Voice messages to the bot work as a fallback chat.
- **Weekly summary** — every Monday 10:00 Rīgas laiks, a Grok-generated
  review of the past week is DM-ed.

### Stack

- **Backend:** Python 3.12, FastAPI (async), aiogram 3 (webhook),
  SQLAlchemy 2 + aiosqlite, APScheduler. Packaged with `uv`.
- **Frontend:** React 18 + Vite + TypeScript + Telegram WebApp JS API.
- **LLM (text + vision):** xAI Grok (`grok-4-fast` chat,
  `grok-imagine-image` image gen) via the OpenAI-compatible
  `https://api.x.ai/v1`.
- **STT / TTS:** OpenAI Whisper-1 + tts-1.
- **Runtime:** two Docker containers on a compose network (backend +
  frontend-nginx). Host-level nginx + Let's Encrypt terminate TLS and
  proxy to the frontend container on `127.0.0.1:8010`.

### Deploy (production)

See [DEPLOY.md](DEPLOY.md) for the exact sequence. High-level:

1. **DNS** — point the subdomain (e.g. `lvaloda.taras.marblecake.fun`) at
   the server IP.
2. **Certificate** — issue / extend a Let's Encrypt cert covering the
   subdomain (nginx plugin works well):
   ```bash
   sudo certbot certonly --nginx --expand -d <your-domain>
   ```
3. **Host nginx site** — copy
   [deploy/nginx/lvaloda.taras.marblecake.fun.conf](deploy/nginx/lvaloda.taras.marblecake.fun.conf)
   to `/etc/nginx/sites-available/`, symlink into `sites-enabled/`, then
   `sudo nginx -t && sudo systemctl reload nginx`.
4. **Secrets** — `cp .env.example .env` and fill `BOT_TOKEN`,
   `XAI_API_KEY`, `OPENAI_API_KEY`. `WEBAPP_URL` and `DATABASE_URL` are
   already set for the container layout.
5. **Run** —
   ```bash
   docker compose up -d --build
   docker compose logs --tail=100
   ```
   Expected log line: `Webhook set to https://<your-domain>/telegram/webhook`.
6. **BotFather** — `/mybots → <bot> → Menu Button`, set URL to your domain.

SQLite lives in a named Docker volume (`lvaloda_data` → `/app/data`). See
DEPLOY.md for backup and rollback commands.

### Local dev (optional, ngrok-based)

Useful if you want hot-reload and to touch the code without rebuilding
containers. Skip if you only plan to run the deployed version.

```bash
# 1. Secrets
cp .env.example .env   # fill BOT_TOKEN, XAI_API_KEY, OPENAI_API_KEY

# 2. Backend
cd backend && uv sync && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 3. Frontend (separate terminal)
cd frontend && npm install && npm run dev   # :5173 proxies /api, /telegram, /healthz → :8000

# 4. ngrok
ngrok http 5173
# Set WEBAPP_URL=https://xxxx.ngrok-free.app in .env, restart the backend.

# 5. BotFather Menu Button → same ngrok URL.
```

### Project layout

```
backend/
  Dockerfile
  pyproject.toml, uv.lock
  app/
    main.py               # FastAPI + aiogram webhook + lifespan scheduler
    config.py             # pydantic-settings
    db/                   # SQLAlchemy models + async session
    auth/telegram.py      # initData HMAC verification
    llm/
      client.py           # AsyncOpenAI (Grok + OpenAI) clients
      scenarios.py, prompts.py
      chat.py             # dialog_reply, exam_reply, analyze_*, russian_hint
      audio.py            # Whisper STT + TTS
    services/             # stats, retrieval, unnatural-phrase extraction
    api/                  # FastAPI routers (chat, exam, picture, phrases, …)
    bot/
      handlers.py         # /start, /remind, voice fallback
      scheduler.py        # daily reminders + weekly summary
    assets/
      minimal_pairs.py, pictures.py, top_phrases.py

frontend/
  Dockerfile
  nginx.conf              # SPA fallback + /api, /telegram, /healthz proxy
  src/
    App.tsx, api.ts, tg.ts, cloud.ts
    hooks/useRecorder.ts
    components/, screens/

deploy/
  nginx/lvaloda.taras.marblecake.fun.conf   # host-nginx site template

docker-compose.yml
.env.example
DEPLOY.md
```

### Cost estimate

Single user, ~30 min/day:

| Service | Approx. monthly |
|---|---|
| xAI Grok (`grok-4-fast`) chat | $3–5 |
| xAI image gen (`grok-imagine-image`) | $0.50–1.50 |
| OpenAI Whisper STT | $5–6 |
| OpenAI TTS | $1–2 |
| **Total** | **~$10–14 / month** |

### Licence

MIT.

---

## Русский

### Что это

Self-hosted Telegram Mini App + бот для ежедневной разговорной практики
латышского. Для взрослых с базой A1/A2, целится в устный экзамен PMLP по
программе «Latvieši un līvi».

Принципы: **никакой грамматической задротни, никакого Anki, никакого
учебникового стиля.** Бот говорит как живой человек в Риге 2025 («как
друзья реально общаются»), мягко правит лексику, держит сессии короткими.

### Фичи (кратко)

- **Saruna** — свободные диалоги в 6 ситуациях, мягкие правки
  `💡 Dabiskāk: ...` с русской подсказкой, разбор в конце.
- **Eksāmena simulācija** — 13 экзаменационных тем PMLP, 10-15 мин с
  follow-up'ами, structured report, анти-повтор «углов».
- **Top frāzes** — 11 × ~25-30 фраз (~290), по 10 карточек за заход,
  `Zinu / Nezinu / Atpakaļ`, история.
- **Shadowing** — 8 живых фраз, TTS 1.0× / 0.75×.
- **Apraksti attēlu** — Grok-генерация картинок × 15 сцен; Grok vision
  сравнивает описание с картинкой, ставит 1-5, выдаёт эталон.
- **Tulkotājs** — RU ↔ LV, авто-детект, TTS.
- **Vārdnīca** — сохранённые слова + авто-собранные ошибки; 🔖 / 🔊.
- **Statistika** — стрик, минуты, 30-дневная heatmap, разбивка по темам.
- **Адаптивная сложность** — fluency_score из прошлых заходов + знакомая
  лексика в ответах бота.
- **CloudStorage resume**, **`/remind 19:00`**, **weekly summary**
  (понедельник 10:00 Rīgas laiks).

### Стек

Python 3.12 · FastAPI · aiogram 3 (webhook) · SQLAlchemy 2 +
aiosqlite · APScheduler · React 18 + Vite + TS · xAI Grok (чат +
картинки) · OpenAI Whisper + TTS. В прод — 2 Docker-контейнера
(backend + frontend-nginx) под хостовым nginx + Let's Encrypt.

### Деплой (прод)

Подробный порядок — в [DEPLOY.md](DEPLOY.md). Коротко:

1. A-запись `<поддомен>` → IP сервера.
2. `sudo certbot certonly --nginx --expand -d <поддомен>` (nginx-плагин
   разруливает HTTP-01 challenge сам, временно добавляя нужные location'ы).
3. Скопировать [deploy/nginx/lvaloda.taras.marblecake.fun.conf](deploy/nginx/lvaloda.taras.marblecake.fun.conf)
   в `/etc/nginx/sites-available/`, линк в `sites-enabled/`,
   `sudo nginx -t && sudo systemctl reload nginx`.
4. `cp .env.example .env` — заполнить `BOT_TOKEN`, `XAI_API_KEY`,
   `OPENAI_API_KEY`. `WEBAPP_URL` и `DATABASE_URL` уже настроены под
   compose-layout.
5. `docker compose up -d --build` — в логах бэка должно быть
   `Webhook set to https://<домен>/telegram/webhook`.
6. BotFather → Menu Button → URL твоего домена.

SQLite живёт в docker volume `lvaloda_data` (`/app/data`). Бэкап,
rollback, рестарт — в DEPLOY.md.

### Локальный dev (опционально, через ngrok)

Если нужен hot-reload и не хочется каждый раз пересобирать контейнеры:

```bash
cp .env.example .env            # BOT_TOKEN, XAI_API_KEY, OPENAI_API_KEY
cd backend && uv sync && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# вторым терминалом:
cd frontend && npm install && npm run dev   # :5173 проксирует /api, /telegram, /healthz → :8000
ngrok http 5173                 # и WEBAPP_URL=<ngrok> в .env + рестарт бэка
```

BotFather Menu Button → тот же ngrok URL.

### Структура и бюджет

См. английскую секцию.

### Лицензия

MIT.

---

## Latviešu

### Kas tas ir

Pašhostēta Telegram Mini App + bots ikdienas latviešu sarunvalodas
praksei. Pieaugušajiem ar A1/A2 līmeni, mērķis — PMLP «Latvieši un
līvi» mutiskais eksāmens.

Pamatprincipi: **nekādu gramatikas urbumu, nekāda Anki, nekāda mācību
grāmatas stila.** Bots runā kā dzīvs cilvēks Rīgā 2025. gadā.

### Funkcijas (īsi)

- **Saruna**, **Eksāmena simulācija**, **Top frāzes** (~290 frāzes 11
  kategorijās), **Shadowing**, **Apraksti attēlu** (Grok bildes + vision
  atgriezeniskā saite), **Tulkotājs** (RU ↔ LV), **Vārdnīca**,
  **Statistika** (strīks, siltumkarte, minūtes), **Adaptīva grūtība**,
  **CloudStorage** atjaunošana, `/remind 19:00`, nedēļas kopsavilkums
  (pirmdiena 10:00 Rīgas laikā).

Detalizēti — skatīt angļu sadaļu augstāk.

### Tehnoloģiju steks

Python 3.12 · FastAPI · aiogram 3 · SQLAlchemy 2 + aiosqlite · React 18
+ Vite · xAI Grok · OpenAI Whisper + TTS. Produkcijā — 2 Docker
konteineri aiz resursdatora nginx + Let's Encrypt.

### Izvietošana (produkcija)

Precīza secība — [DEPLOY.md](DEPLOY.md). Īsumā:

1. DNS A-ieraksts `<apakšdomēns>` → servera IP.
2. `sudo certbot certonly --nginx --expand -d <apakšdomēns>`.
3. Kopēt [deploy/nginx/lvaloda.taras.marblecake.fun.conf](deploy/nginx/lvaloda.taras.marblecake.fun.conf)
   uz `/etc/nginx/sites-available/` → `sites-enabled/`, `nginx -t`,
   `systemctl reload nginx`.
4. `.env` — `BOT_TOKEN`, `XAI_API_KEY`, `OPENAI_API_KEY`.
5. `docker compose up -d --build`.
6. BotFather → Menu Button URL.

### Lokālā izstrāde (ngrok)

Skatīt angļu/krievu sadaļu — pašas komandas.

### Licence

MIT.
