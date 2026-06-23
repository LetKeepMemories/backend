import secrets
from datetime import timedelta

from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password, make_password
from django.middleware.csrf import get_token
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.user.utils.authentication import CookieJWTAuthentication
from apps.user.utils.cookies import clear_auth_cookies, set_auth_cookies
from apps.user.models import PasswordChangeOTP, User
from apps.user.serializers import (
    ChangeEmailSerializer,
    EmailVerificationConfirmSerializer,
    LoginSerializer,
    PasswordChangeOTPConfirmSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ResendVerificationSerializer,
    SignupSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from apps.user.utils.tasks import (
    send_password_change_otp_task,
    send_password_reset_email_task,
    send_verification_email_task,
    send_welcome_email_task,
)
from apps.user.utils.tokens import email_verification_token, password_reset_token

PASSWORD_CHANGE_OTP_VALIDITY_MINUTES = 10

GENERIC_RESET_RESPONSE = {
    "detail": "If an account exists for that email, password reset instructions have been sent."
}
GENERIC_RESEND_RESPONSE = {
    "detail": "If an account exists for that email, a verification link has been sent."
}


def _decode_uid(uid: str):
    try:
        user_pk = force_str(urlsafe_base64_decode(uid))
        return User.objects.get(pk=user_pk)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        return None


def _issue_session(user) -> Response:
    refresh = RefreshToken.for_user(user)
    response = Response(UserSerializer(user).data, status=status.HTTP_200_OK)
    set_auth_cookies(response, access_token=str(refresh.access_token), refresh_token=str(refresh))
    return response


class CSRFTokenView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Auth"],
        summary="Set CSRF Cookie",
        description="Retrieves a CSRF cookie required for stateful authentication operations.",
        responses={200: OpenApiResponse(description="CSRF cookie set.")}
    )
    def get(self, request):
        get_token(request)
        return Response({"detail": "CSRF cookie set."})


class SignupView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(
        tags=["Auth"],
        summary="User Signup",
        description="Registers a new user and sends an email verification link. Returns user details and an HttpOnly cookie containing the JWT.",
        request=SignupSerializer,
        responses={201: UserSerializer}
    )
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        send_verification_email_task(str(user.pk))
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class VerifyEmailView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(
        tags=["Auth"],
        summary="Verify Email",
        description="Verifies the user's email address using the UID and token sent to their inbox.",
        request=EmailVerificationConfirmSerializer,
        responses={
            200: UserSerializer,
            400: OpenApiResponse(description="Invalid or expired verification link.")
        }
    )
    def post(self, request):
        serializer = EmailVerificationConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = _decode_uid(serializer.validated_data["uid"])

        if user is None or not email_verification_token.check_token(user, serializer.validated_data["token"]):
            return Response({"detail": "Invalid or expired verification link."}, status=status.HTTP_400_BAD_REQUEST)

        if not user.is_verified:
            user.is_verified = True
            user.save(update_fields=["is_verified", "updated_at"])
            send_welcome_email_task(str(user.pk))

        return _issue_session(user)


class ResendVerificationView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(
        tags=["Auth"],
        summary="Resend Verification Email",
        description="Resends the verification email if the user is not already verified.",
        request=ResendVerificationSerializer,
        responses={200: OpenApiResponse(description="Verification link sent (if email exists).")}
    )
    def post(self, request):
        serializer = ResendVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email=serializer.validated_data["email"].lower()).first()
        if user and not user.is_verified:
            send_verification_email_task(str(user.pk))
        return Response(GENERIC_RESEND_RESPONSE)


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(
        tags=["Auth"],
        summary="Login User",
        description="Authenticates the user using email and password. Sets the JWT token in an HttpOnly cookie.",
        request=LoginSerializer,
        responses={
            200: UserSerializer,
            401: OpenApiResponse(description="Invalid credentials"),
            403: OpenApiResponse(description="Account deactivated or email not verified")
        }
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            username=serializer.validated_data["email"].lower(),
            password=serializer.validated_data["password"],
        )

        if user is None:
            return Response({"detail": "Invalid email or password."}, status=status.HTTP_401_UNAUTHORIZED)
        if not user.is_active:
            return Response({"detail": "This account has been deactivated."}, status=status.HTTP_403_FORBIDDEN)
        if not user.is_verified:
            return Response(
                {"detail": "Please verify your email before logging in.", "code": "email_not_verified"},
                status=status.HTTP_403_FORBIDDEN,
            )

        return _issue_session(user)


class RefreshView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Auth"],
        summary="Refresh Token",
        description="Refreshes the JWT session using the refresh token stored in the HttpOnly cookie.",
        responses={
            200: OpenApiResponse(description="Token refreshed successfully"),
            401: OpenApiResponse(description="Refresh token missing or invalid")
        }
    )
    def post(self, request):
        CookieJWTAuthentication().enforce_csrf(request)

        raw_token = request.COOKIES.get("refresh_token")
        if not raw_token:
            return Response({"detail": "Refresh token missing."}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            refresh = RefreshToken(raw_token)
            user_id = refresh["user_id"]
            access_token = refresh.access_token
            refresh.blacklist()
            new_refresh = RefreshToken.for_user(User.objects.get(pk=user_id))
        except (TokenError, User.DoesNotExist):
            return Response({"detail": "Refresh token invalid or expired."}, status=status.HTTP_401_UNAUTHORIZED)

        response = Response({"detail": "Token refreshed."})
        set_auth_cookies(response, access_token=str(access_token), refresh_token=str(new_refresh))
        return response


class LogoutView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Auth"],
        summary="Logout User",
        description="Blacklists the current refresh token and clears the authentication cookies.",
        responses={204: OpenApiResponse(description="Logged out successfully")}
    )
    def post(self, request):
        CookieJWTAuthentication().enforce_csrf(request)

        raw_token = request.COOKIES.get("refresh_token")
        if raw_token:
            try:
                RefreshToken(raw_token).blacklist()
            except TokenError:
                pass

        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_auth_cookies(response)
        return response


class MeView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        summary="Get Current User",
        description="Returns details about the currently authenticated user.",
        responses={200: UserSerializer}
    )
    def get(self, request):
        return Response(UserSerializer(request.user).data)

    @extend_schema(
        tags=["Auth"],
        summary="Update Current User",
        description="Updates the first and last name of the currently authenticated user.",
        request=UserUpdateSerializer,
        responses={200: UserSerializer}
    )
    def patch(self, request):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)


class ChangeEmailView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(
        tags=["Auth"],
        summary="Change Email Address",
        description="Updates the user's email, marks them as unverified, sends a verification email, and logs them out.",
        request=ChangeEmailSerializer,
        responses={200: OpenApiResponse(description="Email updated. Verification link sent.")}
    )
    def post(self, request):
        CookieJWTAuthentication().enforce_csrf(request)
        serializer = ChangeEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        user.email = serializer.validated_data["new_email"]
        user.is_verified = False
        user.save(update_fields=["email", "is_verified", "updated_at"])
        
        # Send new verification email
        send_verification_email_task(str(user.pk))
        
        # Blacklist existing sessions
        for outstanding in OutstandingToken.objects.filter(user=user):
            try:
                RefreshToken(outstanding.token).blacklist()
            except TokenError:
                continue

        response = Response({"detail": "Email updated successfully. Please check your inbox to verify."})
        clear_auth_cookies(response)
        return response


class RequestPasswordChangeOTPView(APIView):
    """Emails a 6-digit code so a logged-in user can change their password
    in-app, without the link-based flow that forces a logout."""

    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(
        tags=["Auth"],
        summary="Request Password Change Code",
        description="Emails a 6-digit verification code to the logged-in user, used to confirm a password change.",
        responses={200: OpenApiResponse(description="Code sent.")}
    )
    def post(self, request):
        CookieJWTAuthentication().enforce_csrf(request)

        code = f"{secrets.randbelow(1_000_000):06d}"
        PasswordChangeOTP.objects.create(
            user=request.user,
            code_hash=make_password(code),
            expires_at=timezone.now() + timedelta(minutes=PASSWORD_CHANGE_OTP_VALIDITY_MINUTES),
        )
        send_password_change_otp_task(str(request.user.pk), code)
        return Response({"detail": "A verification code has been sent to your email."})


class ConfirmPasswordChangeOTPView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "otp_confirm"

    @extend_schema(
        tags=["Auth"],
        summary="Confirm Password Change",
        description="Verifies the emailed code and sets the new password.",
        request=PasswordChangeOTPConfirmSerializer,
        responses={
            200: OpenApiResponse(description="Password changed."),
            400: OpenApiResponse(description="Invalid or expired code.")
        }
    )
    def post(self, request):
        CookieJWTAuthentication().enforce_csrf(request)
        serializer = PasswordChangeOTPConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        otp = (
            PasswordChangeOTP.objects.filter(user=request.user, used_at__isnull=True)
            .order_by("-created_at")
            .first()
        )
        if not otp or not otp.is_valid() or not check_password(serializer.validated_data["code"], otp.code_hash):
            return Response({"detail": "Invalid or expired code."}, status=status.HTTP_400_BAD_REQUEST)

        otp.used_at = timezone.now()
        otp.save(update_fields=["used_at", "updated_at"])

        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password", "updated_at"])

        return Response({"detail": "Password changed successfully."})


class PasswordResetRequestView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(
        tags=["Auth"],
        summary="Request Password Reset",
        description="Initiates a password reset flow by sending a reset link to the user's email.",
        request=PasswordResetRequestSerializer,
        responses={200: OpenApiResponse(description="Reset instructions sent")}
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email=serializer.validated_data["email"].lower()).first()
        if user:
            send_password_reset_email_task(str(user.pk))
        return Response(GENERIC_RESET_RESPONSE)


class PasswordResetConfirmView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(
        tags=["Auth"],
        summary="Confirm Password Reset",
        description="Verifies the UID and token, then updates the user's password. Ends all current sessions.",
        request=PasswordResetConfirmSerializer,
        responses={
            200: OpenApiResponse(description="Password has been reset"),
            400: OpenApiResponse(description="Invalid or expired reset link")
        }
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = _decode_uid(serializer.validated_data["uid"])

        if user is None or not password_reset_token.check_token(user, serializer.validated_data["token"]):
            return Response({"detail": "Invalid or expired reset link."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password", "updated_at"])

        # Resetting the password should end every existing session, not just
        # the one making this request. Tokens that are already expired fail
        # to parse here, which is fine — they're unusable either way.
        for outstanding in OutstandingToken.objects.filter(user=user):
            try:
                RefreshToken(outstanding.token).blacklist()
            except TokenError:
                continue

        return Response({"detail": "Password has been reset. Please log in."})
