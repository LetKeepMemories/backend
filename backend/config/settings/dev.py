from decouple import config

from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

CORS_ALLOWED_ORIGINS = ["http://localhost:3000", "http://localhost:5173"]
CSRF_TRUSTED_ORIGINS = ["http://localhost:3000"]

# Cookies over plain HTTP in local dev
AUTH_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

# Run Celery tasks synchronously by default so email/transcription work
# without a separate worker+broker running locally. Override via env once
# you do want to exercise the real async path.
CELERY_TASK_ALWAYS_EAGER = config("CELERY_TASK_ALWAYS_EAGER", default=True, cast=bool)
CELERY_TASK_EAGER_PROPAGATES = True
