import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY                     = os.getenv('SECRET_KEY', 'dev-secret')
    SQLALCHEMY_DATABASE_URI        = os.getenv('DATABASE_URL', 'sqlite:///niwaas.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY        = True
    SESSION_COOKIE_SAMESITE        = 'Lax'

    # In-memory SQLite is per-connection: each new connection opens its own
    # separate, empty database. Without pinning every connection — including
    # the one opened by the background-AI daemon thread in
    # app/routes/complaints.py::_run_ai_suggestions — onto a single shared
    # connection, that thread silently writes into a different (empty)
    # database than the one the request thread just committed to, which
    # surfaces as "0 rows matched" / sqlite3.InterfaceError under load.
    # StaticPool shares one connection across threads; check_same_thread=
    # False is safe here because StaticPool already serializes access to it.
    if SQLALCHEMY_DATABASE_URI == 'sqlite:///:memory:':
        from sqlalchemy.pool import StaticPool
        SQLALCHEMY_ENGINE_OPTIONS = {
            'poolclass': StaticPool,
            'connect_args': {'check_same_thread': False},
        }

    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
    # openai/gpt-oss-20b:free AND openai/gpt-oss-120b:free were both pulled
    # from OpenRouter's free tier within days of each other (Aug 2026) — both
    # 404 with "unavailable for free, use the paid slug instead". Given how
    # fast individual free models are getting delisted right now, pinning to
    # one named model isn't safe. openrouter/free is a router: it auto-picks
    # from whatever's currently free and filters for the features the
    # request needs (tool calling, etc.), so one model going paid/delisted
    # doesn't take the AI features down again.
    OPENROUTER_MODEL   = os.getenv('OPENROUTER_MODEL', 'openrouter/free')