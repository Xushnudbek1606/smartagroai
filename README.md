# SmartAgroAI 🌱

AI-powered agriculture platform for farmers, agronomists and administrators in Uzbekistan and Central Asia.

**Stack:** React + TypeScript + Vite + Tailwind (frontend) · FastAPI + SQLAlchemy 2 + Alembic (backend) · PostgreSQL · Redis · aiogram 3 (Telegram bot) · Docker Compose · Nginx.

---

## Features

| Module | What it does |
|---|---|
| 🔬 AI Plant Doctor | Farmer uploads a plant photo; a vision-LLM provider returns likely disease, confidence, symptoms and recommendations. **No provider configured → the API returns 503 and the UI says so — results are never faked.** |
| 🌦 Weather | Current weather + 7-day forecast per Uzbekistan region/district via OpenWeatherMap with DB caching and crop-care advisories. No API key → clear "not configured" state. |
| 💬 Farmer ↔ Agronomist chat | Real-time WebSocket chat with read receipts, history pagination and server-side participant checks. |
| 🔐 Auth & RBAC | JWT access + rotating refresh tokens, Argon2 hashing, forced password change on first login, role guards on every endpoint, login rate limiting. |
| 🤖 Telegram bot | Account linking via single-use invitation codes, one-time password delivery to the private chat, notifications, `/weather`, `/language`, `/notifications`. Bot down → web platform unaffected. |
| 🌍 i18n | Full UI in **o'zbekcha (lotin), o'zbekcha (кирилл), English, Русский** — switching without reload, persisted to localStorage + profile. Bot messages in all 4 languages too. |
| 🛡 Admin panel | Users CRUD with invitation codes, statistics with activity chart, audit log, system health (DB/AI/weather/Telegram/Redis), landing banner settings. |
| 🌑 Dark Mode | Mandatory dark theme across every page, modal and form. Responsive desktop / tablet / mobile. |

---

## Quick start (Docker)

```bash
cp .env.example .env
# edit .env: set JWT_SECRET_KEY, POSTGRES_PASSWORD, TELEGRAM/WEATHER/AI keys (optional)

docker compose up -d --build
# web:  http://localhost:8080
# api:  http://localhost:8000/docs

# with the Telegram bot:
docker compose --profile bot up -d --build
```

Then sign in:

1. Set `SEED_ADMIN_USERNAME` / `SEED_ADMIN_PASSWORD` in `.env` **before first start** → an admin account is seeded automatically. Or use the backend console to create one.
2. Admin creates a farmer/agronom in **Admin → Users** → a one-time invitation code is shown.
3. The user sends `/account CODE` to your Telegram bot → the bot replies with the username and a one-time password **in the private chat only**.
4. First sign-in forces a password change.

---

## Local development (no Docker)

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/smartagro
export JWT_SECRET_KEY=dev-secret
alembic upgrade head
uvicorn app.main:app --reload
# Swagger: http://localhost:8000/docs
```

SQLite works for quick local runs/tests (`DATABASE_URL=sqlite:///./dev.db`) — PostgreSQL is the production target.

### Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 (proxies /api and /ws to :8000)
npm run build      # production bundle
npm test           # i18n coverage tests (all 4 locales must stay in sync)
```

### Bot

```bash
cd bot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN=... TELEGRAM_WEBHOOK_SECRET=... BACKEND_INTERNAL_URL=http://localhost:8000
python -m bot.main
```

---

## Deploying

The frontend is a static SPA and deploys to Vercel; the API and the Telegram bot
need long-lived processes, so they run on a Docker host/VPS.

### Vercel (frontend)

1. Import the repository and set **Root Directory** to `frontend`.
2. The framework preset is **Vite**; `frontend/vercel.json` pins the build command
   (`npm run build`) and output directory (`dist`).
3. Add these environment variables in the Vercel project (they are baked into the
   bundle at build time, so a change needs a redeploy):
   - `VITE_API_URL` — full API URL *including* the prefix, e.g. `https://api.example.com/api/v1`
   - `VITE_WS_URL` — WebSocket origin only, e.g. `wss://api.example.com`
4. On the backend, add the deployed origin to `BACKEND_CORS_ORIGINS`
   (e.g. `https://smartagroai.vercel.app`) and restart the API.

Client-side routes (`/dashboard`, `/diagnoses/:id`, …) are handled by the SPA
fallback in `frontend/vercel.json`, and uploaded photos/avatars are resolved
against the API host by `assetUrl()` in `frontend/src/services/api.ts`.

---

## Environment variables

See [.env.example](.env.example). The important ones:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `JWT_SECRET_KEY` | **Must be a long random string in production** |
| `TELEGRAM_BOT_TOKEN` | From @BotFather |
| `TELEGRAM_WEBHOOK_SECRET` | Shared secret between bot ↔ backend internal API |
| `WEATHER_API_KEY` | OpenWeatherMap key |
| `AI_PROVIDER` / `AI_API_KEY` / `AI_MODEL_NAME` | Vision model for plant diagnosis (`openai`, `anthropic`, or `custom` OpenAI-compatible endpoint) |
| `UPLOAD_STORAGE_PATH` | Where uploaded plant photos / avatars are stored |

Integration status is always visible at **Admin → System health** and `/api/v1/health`.

### Enabling AI diagnosis

`AI_PROVIDER=none` (default) → the diagnosis endpoint returns `503 ai_not_configured` and the UI explains what to set up.

- **OpenAI:** `AI_PROVIDER=openai`, `AI_API_KEY=sk-...`, `AI_MODEL_NAME=gpt-4o-mini`
- **Anthropic:** `AI_PROVIDER=anthropic`, `AI_API_KEY=sk-ant-...`, `AI_MODEL_NAME=claude-3-5-sonnet-latest`
- **Self-hosted / OpenRouter / Ollama:** `AI_PROVIDER=custom`, `AI_CUSTOM_BASE_URL=https://.../v1`, `AI_MODEL_NAME=...`

The model is prompted to answer in the user's interface language and to never invent pesticide dosages; low confidence (<50%) triggers an explicit "retake photo / ask an agronomist" warning in the UI.

---

## Tests

```bash
# backend (59 tests): auth, RBAC, invitations, farms/crops, diagnoses, weather, chat+WebSocket, admin
cd backend && python -m pytest tests/ -q

# frontend: 4-locale key coverage, placeholder parity, Cyrillic spell-check
cd frontend && npm test
```

---

## Security notes

- Passwords: Argon2id. Only hashes stored; temporary passwords are delivered once via Telegram.
- JWT access tokens (30 min) + rotating refresh tokens (14 days, hashed at rest, revoked on logout/password change).
- Role checks on **every** endpoint server-side; ownership checks for farms/crops/diagnoses/chat.
- Uploads validated by **magic bytes** (not client MIME), size-capped, stored under random names.
- Internal bot API protected by a constant-time-compared shared secret.
- Login and upload rate limiting (in-memory; swap for Redis in multi-replica deployments).
- Audit log for admin/security actions. No secrets or passwords in logs.
- Serve behind HTTPS in production (put TLS in front of Nginx or use a managed proxy).

## Backup & restore

```bash
# backup
docker compose exec db pg_dump -U smartagro smartagro > backup_$(date +%F).sql
docker run --rm -v smartagroai_uploads:/data -v $(pwd):/backup alpine tar czf /backup/uploads_$(date +%F).tgz -C /data .

# restore
cat backup_2026-01-01.sql | docker compose exec -T db psql -U smartagro smartagro
docker run --rm -v smartagroai_uploads:/data -v $(pwd):/backup alpine tar xzf /backup/uploads_2026-01-01.tgz -C /data
```

Schedule `pg_dump` via cron and keep `UPLOAD_STORAGE_PATH` on replicated storage.

## Project layout

```
backend/    FastAPI app (app/api/v1, app/models, app/services, app/integrations, alembic, tests)
frontend/   Vite React TS app (src/pages, src/components, src/locales/*, tests/i18n.test.ts)
bot/        aiogram 3 bot (bot/handlers, bot/locales, bot/services)
docker-compose.yml, .env.example, README.md
```

## API docs

Once running: Swagger UI at `/docs`, OpenAPI schema at `/openapi.json`, health at `/health`.
