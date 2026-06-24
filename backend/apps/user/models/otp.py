import secrets
from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone

from apps.core.utils.models import BaseModel
from apps.user.models.user import User


class EmailOTP(BaseModel):
    """A short-lived, single-use 6-digit code emailed for any flow that
    needs to confirm control of an inbox: verifying a new signup, resetting
    a forgotten password, changing a password in-app, or switching to a new
    email address."""

    class Purpose(models.TextChoices):
        EMAIL_VERIFICATION = "email_verification", "Email Verification"
        PASSWORD_RESET = "password_reset", "Password Reset"
        PASSWORD_CHANGE = "password_change", "Password Change"
        CHANGE_EMAIL = "change_email", "Change Email"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="email_otps")
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    code_hash = models.CharField(max_length=128)
    # Only set for CHANGE_EMAIL — the address being verified, not yet applied
    # to the user record until the code is confirmed.
    new_email = models.EmailField(blank=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def is_valid(self) -> bool:
        return self.used_at is None and self.expires_at > timezone.now()

    @classmethod
    def issue(cls, user, purpose: str, *, validity_minutes: int = 10, new_email: str = ""):
        """Creates a new code for (user, purpose) and returns (otp, raw_code).
        The raw code is never stored — only its hash is."""
        code = f"{secrets.randbelow(1_000_000):06d}"
        otp = cls.objects.create(
            user=user,
            purpose=purpose,
            code_hash=make_password(code),
            new_email=new_email,
            expires_at=timezone.now() + timedelta(minutes=validity_minutes),
        )
        return otp, code

    @classmethod
    def verify(cls, user, purpose: str, code: str):
        """Returns the matching OTP and marks it used, or None if the code
        is wrong, expired, or already used."""
        otp = (
            cls.objects.filter(user=user, purpose=purpose, used_at__isnull=True)
            .order_by("-created_at")
            .first()
        )
        if not otp or not otp.is_valid() or not check_password(code, otp.code_hash):
            return None

        otp.used_at = timezone.now()
        otp.save(update_fields=["used_at", "updated_at"])
        return otp
