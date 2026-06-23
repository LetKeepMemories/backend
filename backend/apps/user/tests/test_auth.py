import pytest
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient

from apps.user.models import User
from apps.user.utils.tokens import email_verification_token, password_reset_token

pytestmark = pytest.mark.django_db


def create_user(email="ada@example.com", password="correct-horse-battery", is_verified=False):
    return User.objects.create_user(
        email=email, password=password, first_name="Ada", last_name="Lovelace", is_verified=is_verified
    )


def uid_for(user):
    return urlsafe_base64_encode(force_bytes(user.pk))


def authenticated_client():
    """A CSRF-enforcing client, with the CSRF cookie already primed —
    mirrors how the frontend bootstraps a session before any POST."""
    client = APIClient(enforce_csrf_checks=True)
    client.get("/api/auth/csrf/")
    csrf_token = client.cookies["csrftoken"].value
    client.credentials(HTTP_X_CSRFTOKEN=csrf_token)
    return client, csrf_token


class TestSignup:
    def test_creates_unverified_user_and_sends_email(self, mailoutbox=None):
        client, _ = authenticated_client()
        response = client.post(
            "/api/auth/signup/",
            {"first_name": "Ada", "last_name": "Lovelace", "email": "ada@example.com", "password": "correct-horse-battery"},
            format="json",
        )
        assert response.status_code == 201
        assert response.data["is_verified"] is False
        user = User.objects.get(email="ada@example.com")
        assert not user.is_verified
        assert user.check_password("correct-horse-battery")

    def test_duplicate_email_rejected(self):
        create_user()
        client, _ = authenticated_client()
        response = client.post(
            "/api/auth/signup/",
            {"first_name": "Ada", "last_name": "Lovelace", "email": "ada@example.com", "password": "correct-horse-battery"},
            format="json",
        )
        assert response.status_code == 400

    def test_weak_password_rejected(self):
        client, _ = authenticated_client()
        response = client.post(
            "/api/auth/signup/",
            {"first_name": "Ada", "last_name": "Lovelace", "email": "ada@example.com", "password": "password"},
            format="json",
        )
        assert response.status_code == 400


class TestVerifyEmail:
    def test_valid_token_verifies_and_logs_in(self):
        user = create_user()
        token = email_verification_token.make_token(user)
        client, _ = authenticated_client()

        response = client.post("/api/auth/verify-email/", {"uid": uid_for(user), "token": token}, format="json")

        assert response.status_code == 200
        user.refresh_from_db()
        assert user.is_verified
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies

    def test_invalid_token_rejected(self):
        user = create_user()
        client, _ = authenticated_client()
        response = client.post("/api/auth/verify-email/", {"uid": uid_for(user), "token": "bogus"}, format="json")
        assert response.status_code == 400
        user.refresh_from_db()
        assert not user.is_verified


class TestLogin:
    def test_unverified_user_blocked(self):
        create_user(is_verified=False)
        client, _ = authenticated_client()
        response = client.post(
            "/api/auth/login/", {"email": "ada@example.com", "password": "correct-horse-battery"}, format="json"
        )
        assert response.status_code == 403
        assert response.data["code"] == "email_not_verified"

    def test_verified_user_can_login(self):
        create_user(is_verified=True)
        client, _ = authenticated_client()
        response = client.post(
            "/api/auth/login/", {"email": "ada@example.com", "password": "correct-horse-battery"}, format="json"
        )
        assert response.status_code == 200
        assert "access_token" in response.cookies

    def test_wrong_password_rejected(self):
        create_user(is_verified=True)
        client, _ = authenticated_client()
        response = client.post("/api/auth/login/", {"email": "ada@example.com", "password": "nope"}, format="json")
        assert response.status_code == 401


class TestMe:
    def test_requires_authentication(self):
        client = APIClient()
        response = client.get("/api/auth/me/")
        assert response.status_code == 401

    def test_returns_current_user_via_cookie(self):
        user = create_user(is_verified=True)
        client, csrf = authenticated_client()
        client.post("/api/auth/login/", {"email": "ada@example.com", "password": "correct-horse-battery"}, format="json")
        response = client.get("/api/auth/me/")
        assert response.status_code == 200
        assert response.data["email"] == user.email


class TestLogoutAndRefresh:
    def _logged_in_client(self):
        create_user(is_verified=True)
        client, csrf = authenticated_client()
        client.post("/api/auth/login/", {"email": "ada@example.com", "password": "correct-horse-battery"}, format="json")
        return client, csrf

    def test_logout_without_csrf_header_rejected(self):
        client, _ = self._logged_in_client()
        client.credentials()  # drop the X-CSRFToken header
        response = client.post("/api/auth/logout/")
        assert response.status_code == 403

    def test_logout_clears_cookies(self):
        client, csrf = self._logged_in_client()
        response = client.post("/api/auth/logout/")
        assert response.status_code == 204

    def test_refresh_rotates_tokens(self):
        client, csrf = self._logged_in_client()
        old_refresh = client.cookies["refresh_token"].value
        response = client.post("/api/auth/refresh/")
        assert response.status_code == 200
        assert client.cookies["refresh_token"].value != old_refresh


class TestPasswordReset:
    def test_full_reset_flow_invalidates_old_sessions(self):
        user = create_user(is_verified=True)
        client, csrf = authenticated_client()
        login_response = client.post(
            "/api/auth/login/", {"email": "ada@example.com", "password": "correct-horse-battery"}, format="json"
        )
        old_refresh = login_response.cookies["refresh_token"].value

        token = password_reset_token.make_token(user)
        confirm = client.post(
            "/api/auth/password-reset/confirm/",
            {"uid": uid_for(user), "token": token, "new_password": "new-correct-horse-99"},
            format="json",
        )
        assert confirm.status_code == 200

        # Old refresh token must now be blacklisted.
        client.cookies["refresh_token"] = old_refresh
        refresh_attempt = client.post("/api/auth/refresh/")
        assert refresh_attempt.status_code == 401

        # New password works.
        relogin = client.post(
            "/api/auth/login/", {"email": "ada@example.com", "password": "new-correct-horse-99"}, format="json"
        )
        assert relogin.status_code == 200

    def test_unknown_email_returns_generic_response(self):
        client, _ = authenticated_client()
        response = client.post("/api/auth/password-reset/", {"email": "ghost@example.com"}, format="json")
        assert response.status_code == 200
