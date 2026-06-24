from django.conf import settings

from apps.core.utils.email import send_email
from apps.user.models import EmailOTP


def send_verification_email_task(user_id):
    from apps.user.models import User

    user = User.objects.get(pk=user_id)
    _, code = EmailOTP.issue(user, EmailOTP.Purpose.EMAIL_VERIFICATION, validity_minutes=15)
    send_email(
        to=user.email,
        subject=f"Email Verification",
        template="verify_email.html",
        context={"first_name": user.first_name, "code": code},
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
    _, code = EmailOTP.issue(user, EmailOTP.Purpose.PASSWORD_RESET, validity_minutes=15)
    send_email(
        to=user.email,
        subject=f"Password Reset Code",
        template="password_reset.html",
        context={"first_name": user.first_name, "code": code},
    )


def send_password_change_otp_task(user_id, code):
    from apps.user.models import User

    user = User.objects.get(pk=user_id)
    send_email(
        to=user.email,
        subject=f"Change Password verification",
        template="password_change_otp.html",
        context={"first_name": user.first_name, "code": code},
    )


def send_change_email_otp_task(user_id, new_email, code):
    from apps.user.models import User

    user = User.objects.get(pk=user_id)
    send_email(
        to=new_email,
        subject=f"Change Email verification",
        template="change_email.html",
        context={"first_name": user.first_name, "code": code, "new_email": new_email},
    )
