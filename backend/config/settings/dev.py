from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=["http://localhost:3000"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=["http://localhost:3000"])

# Cookies over plain HTTP in local dev.
AUTH_COOKIE_SECURE = env.bool("AUTH_COOKIE_SECURE", default=False)
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

# Run Celery tasks synchronously by default so email/transcription work
# without a separate worker+broker running locally. Override via env once
# you do want to exercise the real async path.
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=True)
CELERY_TASK_EAGER_PROPAGATES = True
