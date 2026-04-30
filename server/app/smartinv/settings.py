import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "smartinv-dev-secret-key")
DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = [host.strip() for host in os.getenv("DJANGO_ALLOWED_HOSTS", "*").split(",") if host.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "inventory",
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

ROOT_URLCONF = "smartinv.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "smartinv.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.postgresql"),
        "NAME": os.getenv("POSTGRES_DB", "smartinv"),
        "USER": os.getenv("POSTGRES_USER", "smartinv"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "smartinv"),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticatedOrReadOnly"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
}

SPECTACULAR_SETTINGS = {
    "TITLE": "SmartInv API",
    "DESCRIPTION": "API для системы учета материальных активов и интеграции с 1С УНФ",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}


def _env_bool(key: str, default: bool) -> bool:
    v = os.getenv(key)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = int(os.getenv("CELERY_TASK_TIME_LIMIT", "900"))
CELERY_TASK_ROUTES = {
    "inventory.tasks.run_vision_classification": {"queue": "vision"},
    "inventory.tasks.run_gigachat_condition_summary": {"queue": "llm"},
}

# GigaChat: в Authorization для OAuth передаётся GIGACHAT_AUTH_KEY (часто строка вида "Basic <base64>").
GIGACHAT_AUTH_KEY = os.getenv("GIGACHAT_AUTH_KEY", "").strip()
GIGACHAT_CLIENT_ID = os.getenv("GIGACHAT_CLIENT_ID", os.getenv("CLIENT_ID", "")).strip()
GIGACHAT_SCOPE = os.getenv("GIGACHAT_SCOPE", os.getenv("SCOPE", "GIGACHAT_API_PERS")).strip()
GIGACHAT_OAUTH_URL = os.getenv(
    "GIGACHAT_OAUTH_URL",
    "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
)
GIGACHAT_API_BASE = os.getenv("GIGACHAT_API_BASE", "https://gigachat.devices.sberbank.ru/api/v1")
GIGACHAT_MODEL = os.getenv("GIGACHAT_MODEL", "GigaChat")
GIGACHAT_VERIFY_SSL = _env_bool("GIGACHAT_VERIFY_SSL", True)

# ConvNeXt: 5 классов состояния по фото. Веса после `python manage.py train_condition_classifier`.
CONDITION_CLASSIFIER_WEIGHTS = os.getenv(
    "CONDITION_CLASSIFIER_WEIGHTS",
    str(BASE_DIR / "weights" / "asset_condition_convnext.pt"),
).strip()
# Папки с разметкой: <slug>/*.jpg (slug из inventory.ml.condition_classes.CLASS_SLUGS)
CONDITION_TRAINING_DATA_DIR = os.getenv(
    "CONDITION_TRAINING_DATA_DIR",
    str(BASE_DIR / "training_data" / "asset_condition"),
).strip()
