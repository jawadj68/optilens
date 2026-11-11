import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DEBUG = os.environ.get("OPTILENS_DEBUG", "1").lower() in ("1", "true", "yes")

_secret = os.environ.get("OPTILENS_SECRET_KEY")
if not _secret:
    if DEBUG:
        _secret = "optilens-dev-only-change-in-production"
    else:
        raise RuntimeError("OPTILENS_SECRET_KEY is required when DEBUG is False.")
SECRET_KEY = _secret

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("OPTILENS_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if h.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "patients.apps.PatientsConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "optilens_site.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "optilens_site.wsgi.application"

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

if os.environ.get("OPTILENS_DB_ENGINE") == "postgresql":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("OPTILENS_DB_NAME", "optilens"),
            "USER": os.environ.get("OPTILENS_DB_USER", "postgres"),
            "PASSWORD": os.environ.get("OPTILENS_DB_PASSWORD", ""),
            "HOST": os.environ.get("OPTILENS_DB_HOST", "localhost"),
            "PORT": os.environ.get("OPTILENS_DB_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": DATA_DIR / "optilens.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 4},
    },
]

LANGUAGE_CODE = "fr"
TIME_ZONE = "Asia/Beirut"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "optilens:patient_list"
LOGOUT_REDIRECT_URL = "login"
