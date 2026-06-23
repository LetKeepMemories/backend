from django.urls import path

from apps.user.views import (
    ChangeEmailView,
    ConfirmPasswordChangeOTPView,
    CSRFTokenView,
    LoginView,
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RefreshView,
    RequestPasswordChangeOTPView,
    ResendVerificationView,
    SignupView,
    VerifyEmailView,
)

urlpatterns = [
    path("csrf/", CSRFTokenView.as_view(), name="csrf"),
    path("signup/", SignupView.as_view(), name="signup"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("refresh/", RefreshView.as_view(), name="refresh"),
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("change-email/", ChangeEmailView.as_view(), name="change-email"),
    path("resend-verification/", ResendVerificationView.as_view(), name="resend-verification"),
    path("password-reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("password-change/request-otp/", RequestPasswordChangeOTPView.as_view(), name="password-change-request-otp"),
    path("password-change/confirm/", ConfirmPasswordChangeOTPView.as_view(), name="password-change-confirm"),
]
