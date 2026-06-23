from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """Same scheme Django uses for password resets, but the hash is keyed off
    `is_verified` instead of the password — so a token is automatically
    invalidated once the account has been verified (or stays valid across
    unrelated password changes, which a vanilla PasswordResetTokenGenerator
    would not allow).
    """

    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{user.is_verified}{timestamp}"


email_verification_token = EmailVerificationTokenGenerator()
password_reset_token = PasswordResetTokenGenerator()
