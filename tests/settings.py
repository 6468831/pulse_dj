from __future__ import annotations

SECRET_KEY = "tests"
ROOT_URLCONF = "tests.urls"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "sitepulse.django",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

SITEPULSE = {
    "PROJECT_ID": "test-project",
    "SECRET": "test-secret",
    "INGEST_URL": "http://sitepulse.test/api/v1/ingest/",
    "PUBLIC_EVENT_PATH": "api/runtime/events/",
    "DELIVERY_MODE": "database_outbox",
}
