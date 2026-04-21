# Server Deploy Notes

Production host: single Ubuntu box behind host-level nginx + Let's Encrypt.
App runs as two Docker containers (backend FastAPI + frontend nginx) on an
isolated compose network. Host-nginx proxies `https://lvaloda.taras.marblecake.fun`
→ `127.0.0.1:8010` (frontend container).

## One-time setup

### 1. DNS
Add an A-record in the `marblecake.fun` DNS panel:
```
lvaloda.taras  A  82.27.2.81
```
Verify:
```bash
dig +short lvaloda.taras.marblecake.fun
```

### 2. SSL (expand existing cert)
```bash
sudo certbot certonly --expand --webroot -w /var/www/taras.marblecake.fun \
  -d taras.marblecake.fun \
  -d alice.taras.marblecake.fun \
  -d lvaloda.taras.marblecake.fun
```
Confirm: `sudo certbot certificates | grep -A3 lvaloda`.

### 3. Host nginx site
```bash
sudo cp deploy/nginx/lvaloda.taras.marblecake.fun.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/lvaloda.taras.marblecake.fun.conf \
          /etc/nginx/sites-enabled/lvaloda.taras.marblecake.fun
sudo nginx -t && sudo systemctl reload nginx
```

### 4. `.env`
Copy `.env.example` → `.env` and fill `BOT_TOKEN`, `XAI_API_KEY`, `OPENAI_API_KEY`.
`WEBAPP_URL` and `DATABASE_URL` are already set to production defaults.

### 5. Bring up
```bash
docker compose up -d --build
docker compose logs --tail=100
```
Expected log line: `Webhook set to https://lvaloda.taras.marblecake.fun/telegram/webhook`.

### 6. BotFather
```
/mybots → <bot> → Bot Settings → Menu Button → Configure Menu Button
URL:  https://lvaloda.taras.marblecake.fun
Text: Parunāties
```

## Verification

```bash
curl -sS  https://lvaloda.taras.marblecake.fun/healthz        # → {"ok":true}
curl -sSI https://lvaloda.taras.marblecake.fun/               # → 200, text/html
docker compose ps                                             # both services Up
```

## Maintenance

| Action            | Command                                     |
|-------------------|---------------------------------------------|
| Restart           | `docker compose restart`                    |
| Update from git   | `git pull && docker compose up -d --build`  |
| Logs (follow)     | `docker compose logs -f`                    |
| Backup SQLite     | `docker run --rm -v lvaloda_lvaloda_data:/d -v "$PWD":/b alpine cp /d/lvaloda.db /b/lvaloda.db.bak` |
| Stop              | `docker compose down`                       |
| Full rollback     | `docker compose down && sudo rm /etc/nginx/sites-enabled/lvaloda.taras.marblecake.fun && sudo nginx -t && sudo systemctl reload nginx` |

The SQLite DB lives in the `lvaloda_lvaloda_data` Docker volume; `docker compose
down` keeps it. Only `docker volume rm lvaloda_lvaloda_data` deletes it.
