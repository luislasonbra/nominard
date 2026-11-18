"""
config.py
Toda la configuración sale de variables de entorno, para que el mismo código
funcione en tu PC (SQLite), en Docker y en Cloud Run (PostgreSQL).
"""
import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def env_bool(nombre, default=False):
    valor = os.environ.get(nombre)
    if valor is None:
        return default
    return valor.strip().lower() in ("1", "true", "si", "sí", "yes", "on")


def database_uri():
    """DATABASE_URL si existe; si no, el archivo SQLite local de siempre."""
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        return "sqlite:///" + os.path.join(BASE_DIR, "nominard.db")
    # Algunos proveedores (Neon, Supabase, Heroku) entregan "postgres://..."
    for prefijo in ("postgres://", "postgresql://"):
        if url.startswith(prefijo):
            return "postgresql+psycopg2://" + url[len(prefijo):]
    return url


# APP_ENV=production se define al desplegar en Cloud Run.
IS_PROD = os.environ.get("APP_ENV", "development").lower() == "production"


class Config:
    SQLALCHEMY_DATABASE_URI = database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    SECRET_KEY = os.environ.get("SECRET_KEY", "")

    # Firebase Hosting solo reenvía a Cloud Run la cookie llamada "__session".
    SESSION_COOKIE_NAME = "__session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", IS_PROD)
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    # El token de "olvidé mi contraseña" se muestra en pantalla porque el
    # proyecto aún no envía correos. Solo es aceptable en desarrollo.
    EXPOSE_RESET_TOKEN = env_bool("EXPOSE_RESET_TOKEN", not IS_PROD)

    # En producción nadie debe poder crearse una cuenta y ver la nómina.
    # Con ALLOW_REGISTRATION=1 se abre el registro de forma temporal.
    ALLOW_REGISTRATION = env_bool("ALLOW_REGISTRATION", not IS_PROD)

    # Si no hay usuarios, se crea este administrador al arrancar.
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")


def validar_config():
    """En producción no se permite arrancar sin una SECRET_KEY real."""
    if IS_PROD and len(Config.SECRET_KEY) < 24:
        raise RuntimeError(
            "En producción debes definir SECRET_KEY con al menos 24 caracteres."
        )
    if not Config.SECRET_KEY:
        Config.SECRET_KEY = "solo-para-desarrollo-local"
