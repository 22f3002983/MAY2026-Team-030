import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY                     = os.getenv('SECRET_KEY', 'dev-secret')
    SQLALCHEMY_DATABASE_URI        = os.getenv('DATABASE_URL', 'sqlite:///niwaas.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY        = True
    SESSION_COOKIE_SAMESITE        = 'Lax'

    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
    OPENROUTER_MODEL   = os.getenv('OPENROUTER_MODEL', 'openai/gpt-oss-20b:free')