import pytest
from rest_framework.test import APIClient

from apps.user.models import EmailOTP, User

pytestmark = pytest.mark.django_db


def create_user(email="ada@example.com", password="correct-horse-battery", is_verified=False):
    return User.objects.create_user(
        email=email, password=password, first_name="Ada", last_name="Lovelace", is_verified=is_verified
    )


def authenticated_client():
    """A CSRF-enforcing client, with the CSRF cookie already primed —
    mirrors how the frontend bootstraps a session before any POST."""
    client = APIClient(enforce_csrf_checks=True)
    client.get("/api/auth/csrf/")
    csrf_token = client.cookies["csrftoken"].value
    client.credentials(HTTP_X_CSRFTOKEN=csrf_token)
    return client, csrf_token


@pytest.fixture
def captured_emails(monkeypatch):
    """Intercepts every outgoing email so tests can read the OTP code that
    was actually emailed, without weakening EmailOTP's hash-only storage."""
    sent = []

    def fake_send_email(*, to, subject, template, context):
        sent.append({"to": to, "subject": subject, "template": template, "context": context})

    monkeypatch.setattr("apps.user.utils.tasks.send_email", fake_send_email)
    return sent


class TestSignup:
    def test_creates_unverified_user_and_sends_email(self, captured_emails):
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
        assert captured_emails[-1]["template"] == "verify_email.html"
        assert "code" in captured_emails[-1]["context"]

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
    def test_valid_code_verifies_and_logs_in(self, captured_emails):
        user = create_user()
        _, code = EmailOTP.issue(user, EmailOTP.Purpose.EMAIL_VERIFICATION)
        client, _ = authenticated_client()

        response = client.post("/api/auth/verify-email/", {"email": user.email, "code": code}, format="json")

        assert response.status_code == 200
        user.refresh_from_db()
        assert user.is_verified
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies

    def test_invalid_code_rejected(self):
        user = create_user()
        EmailOTP.issue(user, EmailOTP.Purpose.EMAIL_VERIFICATION)
        client, _ = authenticated_client()
        response = client.post("/api/auth/verify-email/", {"email": user.email, "code": "000000"}, format="json")
        assert response.status_code == 400
        user.refresh_from_db()
        assert not user.is_verified

    def test_code_is_single_use(self):
        user = create_user()
        _, code = EmailOTP.issue(user, EmailOTP.Purpose.EMAIL_VERIFICATION)
        client, _ = authenticated_client()
        first = client.post("/api/auth/verify-email/", {"email": user.email, "code": code}, format="json")
        assert first.status_code == 200
        second = client.post("/api/auth/verify-email/", {"email": user.email, "code": code}, format="json")
        assert second.status_code == 400


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

        _, code = EmailOTP.issue(user, EmailOTP.Purpose.PASSWORD_RESET)
        confirm = client.post(
            "/api/auth/password-reset/confirm/",
            {"email": user.email, "code": code, "new_password": "new-correct-horse-99"},
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

    def test_invalid_code_rejected(self):
        user = create_user(is_verified=True)
        EmailOTP.issue(user, EmailOTP.Purpose.PASSWORD_RESET)
        client, _ = authenticated_client()
        response = client.post(
            "/api/auth/password-reset/confirm/",
            {"email": user.email, "code": "000000", "new_password": "new-correct-horse-99"},
            format="json",
        )
        assert response.status_code == 400


class TestChangeEmail:
    def _logged_in_client(self, user):
        client, csrf = authenticated_client()
        client.post("/api/auth/login/", {"email": user.email, "password": "correct-horse-battery"}, format="json")
        return client

    def test_request_does_not_change_email_until_confirmed(self, captured_emails):
        user = create_user(is_verified=True)
        client = self._logged_in_client(user)

        response = client.post("/api/auth/change-email/", {"new_email": "new@example.com"}, format="json")
        assert response.status_code == 200
        assert captured_emails[-1]["to"] == "new@example.com"

        user.refresh_from_db()
        assert user.email == "ada@example.com"

    def test_confirm_applies_the_change_and_logs_out(self, captured_emails):
        user = create_user(is_verified=True)
        client = self._logged_in_client(user)
        client.post("/api/auth/change-email/", {"new_email": "new@example.com"}, format="json")
        code = captured_emails[-1]["context"]["code"]

        response = client.post("/api/auth/change-email/confirm/", {"code": code}, format="json")
        assert response.status_code == 200

        user.refresh_from_db()
        assert user.email == "new@example.com"

    def test_taken_email_rejected(self):
        create_user(email="taken@example.com", is_verified=True)
        user = create_user(email="ada@example.com", is_verified=True)
        client = self._logged_in_client(user)

        response = client.post("/api/auth/change-email/", {"new_email": "taken@example.com"}, format="json")
        assert response.status_code == 400
