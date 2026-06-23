from django.db import models
from django.utils import timezone

from apps.core.utils.models import BaseModel
from apps.user.models.user import User


class PasswordChangeOTP(BaseModel):
    """A short-lived, single-use code emailed to a logged-in user who wants
    to change their password without leaving the app (unlike the link-based
    forgot-password flow, which is for logged-out users)."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="password_change_otps")
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def is_valid(self) -> bool:
        return self.used_at is None and self.expires_at > timezone.now()
