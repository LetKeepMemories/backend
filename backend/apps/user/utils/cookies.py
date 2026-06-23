from django.conf import settings

REFRESH_COOKIE_PATH = "/api/auth/"


def set_auth_cookies(response, *, access_token: str, refresh_token: str) -> None:
    access_lifetime = settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"]
    refresh_lifetime = settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"]

    response.set_cookie(
        settings.AUTH_COOKIE_ACCESS,
        access_token,
        max_age=int(access_lifetime.total_seconds()),
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        domain=settings.AUTH_COOKIE_DOMAIN,
        path="/",
    )
    response.set_cookie(
        settings.AUTH_COOKIE_REFRESH,
        refresh_token,
        max_age=int(refresh_lifetime.total_seconds()),
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        domain=settings.AUTH_COOKIE_DOMAIN,
        path=REFRESH_COOKIE_PATH,
    )


def clear_auth_cookies(response) -> None:
    response.delete_cookie(settings.AUTH_COOKIE_ACCESS, domain=settings.AUTH_COOKIE_DOMAIN, path="/")
    response.delete_cookie(
        settings.AUTH_COOKIE_REFRESH, domain=settings.AUTH_COOKIE_DOMAIN, path=REFRESH_COOKIE_PATH
    )
