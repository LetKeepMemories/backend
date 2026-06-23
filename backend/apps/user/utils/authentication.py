from django.conf import settings
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken


class CookieJWTAuthentication(JWTAuthentication):
    """Reads the access token from an httpOnly cookie instead of the
    Authorization header, so the JWT never has to live in JS-reachable
    storage (localStorage/sessionStorage) and can't be lifted by an XSS
    payload. Falls back to the header so the browsable API / Swagger UI
    (and any future server-to-server callers) still work with a bearer token.

    Cookie-based auth is sent automatically by the browser on every request
    to our domain, which makes it CSRF-able unless we check a token the
    attacker's page can't read — so unlike header auth, cookie auth here
    also enforces the standard Django CSRF double-submit check.
    """

    def authenticate(self, request):
        header = self.get_header(request)
        if header is not None:
            return super().authenticate(request)

        raw_token = request.COOKIES.get(settings.AUTH_COOKIE_ACCESS)
        if raw_token is None:
            return None

        try:
            validated_token = self.get_validated_token(raw_token)
        except InvalidToken:
            return None

        self.enforce_csrf(request)
        return self.get_user(validated_token), validated_token

    def enforce_csrf(self, request):
        SessionAuthentication().enforce_csrf(request)
