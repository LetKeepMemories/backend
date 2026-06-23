from django.conf import settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.core.utils.email import send_email
from apps.user.utils.tokens import email_verification_token, password_reset_token


def _uid_for(user) -> str:
    return urlsafe_base64_encode(force_bytes(user.pk))


def send_verification_email_task(user_id):
    from apps.user.models import User

    user = User.objects.get(pk=user_id)
    token = email_verification_token.make_token(user)
    link = f"{settings.FRONTEND_URL}/verify-email?uid={_uid_for(user)}&token={token}"
    send_email(
        to=user.email,
        subject="Verify your Lets Keep Memories account",
        template="verify_email.html",
        context={"first_name": user.first_name, "verification_link": link},
    )


def send_welcome_email_task(user_id):
    from apps.user.models import User

    user = User.objects.get(pk=user_id)
    send_email(
        to=user.email,
        subject="Welcome to Lets Keep Memories",
        template="welcome.html",
        context={"first_name": user.first_name, "login_link": f"{settings.FRONTEND_URL}/login"},
    )


def send_password_reset_email_task(user_id):
    from apps.user.models import User

    user = User.objects.get(pk=user_id)
    token = password_reset_token.make_token(user)
    link = f"{settings.FRONTEND_URL}/reset-password?uid={_uid_for(user)}&token={token}"
    send_email(
        to=user.email,
        subject="Reset your Lets Keep Memories password",
        template="password_reset.html",
        context={"first_name": user.first_name, "reset_link": link},
    )


def send_password_change_otp_task(user_id, code):
    from apps.user.models import User

    user = User.objects.get(pk=user_id)
    send_email(
        to=user.email,
        subject=f"{code} is your Lets Keep Memories verification code",
        template="password_change_otp.html",
        context={"first_name": user.first_name, "code": code},
    )
