# MAY2026-Team-030

Niwaas — a society/RWA management platform with role-based dashboards for
residents, secretaries, and security staff. Handles maintenance dues,
complaints, notices, amenities, vendors, visitors, emergencies, and more,
with a few AI-assisted features (auto-categorization, duplicate detection,
bill analysis, amenity recommendations) and optional Telegram notifications.

## Tech stack

- **Frontend:** Vue 3 + Vite
- **Backend:** Flask, Flask-SQLAlchemy, Flask-Login
- **Database:** SQLite (default) — swappable via `DATABASE_URL`
- **AI:** OpenRouter (chat completions)
- **Notifications:** Telegram Bot API (optional)

## Project structure

```
.
├── frontend/   # Vue 3 + Vite app
└── backend/    # Flask API, models, routes, AI services, tests
```

---

## Backend

### Setup

```sh
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Environment variables

Copy `.env.example` to `.env` and fill in the values:

```sh
cp .env.example .env
```

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | No (has a dev default) | Flask session secret — set a real value in production |
| `DATABASE_URL` | No (defaults to local SQLite) | e.g. `sqlite:///niwaas.db` or a Postgres URL |
| `FLASK_ENV` / `FLASK_DEBUG` | No | Standard Flask dev settings |
| `OPENROUTER_API_KEY` | Yes, for AI features | Get a free key at [openrouter.ai/keys](https://openrouter.ai/keys). Powers AI complaint categorization, duplicate detection, bill analysis, amenity recommendations, and the AI assistant. Without it, these features are silently skipped. |
| `OPENROUTER_MODEL` | No (defaults to `openai/gpt-oss-20b:free`) | Which OpenRouter model to use |
| `TELEGRAM_BOT_TOKEN` | No | Token from [@BotFather](https://t.me/BotFather). Enables Telegram delivery for reminders/notifications. Without it, the bot is disabled and this is logged, not an error. |
| `TELEGRAM_BOT_USERNAME` | No | Your bot's `@username`, used when generating deep links |

### Run the backend

```sh
python run.py
```

Runs at `http://localhost:5000` by default.

### Seed demo data (optional)

With the backend running in another terminal:

```sh
python seed.py
```

Creates a demo secretary, security guard, and 6 residents — see the top of
`seed.py` for login credentials.

### Run tests

```sh
pytest
```

Warnings from third-party deprecations are filtered via `pytest.ini`.

---

## Frontend

### Setup

```sh
cd frontend
npm install
```

### Compile and hot-reload for development

```sh
npm run dev
```

### Compile and minify for production

```sh
npm run build
```

By default the frontend expects the backend API at `http://localhost:5000`
(see `frontend/src/api/axios.js`) — update the base URL there if your
backend runs elsewhere.

### Recommended IDE setup

[VS Code](https://code.visualstudio.com/) + [Vue (Official)](https://marketplace.visualstudio.com/items?itemName=Vue.volar) (and disable Vetur).

### Recommended browser setup

- Chromium-based browsers (Chrome, Edge, Brave, etc.):
  - [Vue.js devtools](https://chromewebstore.google.com/detail/vuejs-devtools/nhdogjmejiglipccpnnnanhbledajbpd)
  - [Turn on Custom Object Formatter in Chrome DevTools](http://bit.ly/object-formatters)
- Firefox:
  - [Vue.js devtools](https://addons.mozilla.org/en-US/firefox/addon/vue-js-devtools/)
  - [Turn on Custom Object Formatter in Firefox DevTools](https://fxdx.dev/firefox-devtools-custom-object-formatters/)

### Customize configuration

See the [Vite Configuration Reference](https://vite.dev/config/).

---

## Running the full stack locally

```sh
# terminal 1
cd backend && source venv/bin/activate && python run.py

# terminal 2
cd frontend && npm run dev
```

Then open the frontend dev server URL printed by Vite (typically
`http://localhost:5173`).
