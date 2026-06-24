from .base import *  # noqa: F401,F403

DEBUG = False

# Frontend and backend live on different *.vercel.app subdomains, which the
# browser treats as separate sites, so auth cookies must be SameSite=None
# (requires Secure=True, already the default) to be sent on cross-site
# fetch/XHR calls.
AUTH_COOKIE_SAMESITE = "None"

# Vercel handles HTTPS termination at the edge
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SESSION_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"
