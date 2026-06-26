from django.contrib.auth import authenticate
from django.conf import settings
from django.middleware.csrf import get_token
import requests
import urllib.parse
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
from apps.user.models import EmailOTP, User
from apps.user.serializers import (
    ChangeEmailConfirmSerializer,
    ChangeEmailRequestSerializer,
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
    send_change_email_otp_task,
    send_password_change_otp_task,
    send_password_reset_email_task,
    send_verification_email_task,
    send_welcome_email_task,
)

GENERIC_RESET_RESPONSE = {
    "detail": "If an account exists for that email, a password reset code has been sent."
}
GENERIC_RESEND_RESPONSE = {
    "detail": "If an account exists for that email, a verification code has been sent."
}


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
        description="Registers a new user and sends an email verification code. Returns user details and an HttpOnly cookie containing the JWT.",
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
        description="Verifies the user's email address using the code sent to their inbox.",
        request=EmailVerificationConfirmSerializer,
        responses={
            200: UserSerializer,
            400: OpenApiResponse(description="Invalid or expired verification code.")
        }
    )
    def post(self, request):
        serializer = EmailVerificationConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email=serializer.validated_data["email"].lower()).first()

        otp = user and EmailOTP.verify(user, EmailOTP.Purpose.EMAIL_VERIFICATION, serializer.validated_data["code"])
        if otp is None:
            return Response({"detail": "Invalid or expired verification code."}, status=status.HTTP_400_BAD_REQUEST)

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
        description="Resends the verification code if the user is not already verified.",
        request=ResendVerificationSerializer,
        responses={200: OpenApiResponse(description="Verification code sent (if email exists).")}
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


class ChangeEmailRequestView(APIView):
    """Sends a code to the *new* address to prove the user actually owns
    it before anything on the account changes."""

    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(
        tags=["Auth"],
        summary="Request Email Change",
        description="Sends a 6-digit code to the new email address. The account isn't changed until the code is confirmed.",
        request=ChangeEmailRequestSerializer,
        responses={200: OpenApiResponse(description="Verification code sent to the new address.")}
    )
    def post(self, request):
        CookieJWTAuthentication().enforce_csrf(request)
        serializer = ChangeEmailRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_email = serializer.validated_data["new_email"]
        _, code = EmailOTP.issue(request.user, EmailOTP.Purpose.CHANGE_EMAIL, new_email=new_email)
        send_change_email_otp_task(str(request.user.pk), new_email, code)
        return Response({"detail": f"A verification code has been sent to {new_email}."})


class ChangeEmailConfirmView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "otp_confirm"

    @extend_schema(
        tags=["Auth"],
        summary="Confirm Email Change",
        description="Verifies the code sent to the new address, applies the email change, and logs the user out everywhere.",
        request=ChangeEmailConfirmSerializer,
        responses={
            200: OpenApiResponse(description="Email updated."),
            400: OpenApiResponse(description="Invalid or expired code.")
        }
    )
    def post(self, request):
        CookieJWTAuthentication().enforce_csrf(request)
        serializer = ChangeEmailConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        otp = EmailOTP.verify(request.user, EmailOTP.Purpose.CHANGE_EMAIL, serializer.validated_data["code"])
        if otp is None:
            return Response({"detail": "Invalid or expired code."}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        user.email = otp.new_email
        user.save(update_fields=["email", "updated_at"])

        for outstanding in OutstandingToken.objects.filter(user=user):
            try:
                RefreshToken(outstanding.token).blacklist()
            except TokenError:
                continue

        response = Response({"detail": "Email updated successfully. Please log in again."})
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

        _, code = EmailOTP.issue(request.user, EmailOTP.Purpose.PASSWORD_CHANGE)
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

        otp = EmailOTP.verify(request.user, EmailOTP.Purpose.PASSWORD_CHANGE, serializer.validated_data["code"])
        if otp is None:
            return Response({"detail": "Invalid or expired code."}, status=status.HTTP_400_BAD_REQUEST)

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
        description="Initiates a password reset flow by sending a 6-digit code to the user's email.",
        request=PasswordResetRequestSerializer,
        responses={200: OpenApiResponse(description="Reset code sent")}
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
        description="Verifies the emailed code, then updates the user's password. Ends all current sessions.",
        request=PasswordResetConfirmSerializer,
        responses={
            200: OpenApiResponse(description="Password has been reset"),
            400: OpenApiResponse(description="Invalid or expired reset code")
        }
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email=serializer.validated_data["email"].lower()).first()

        otp = user and EmailOTP.verify(user, EmailOTP.Purpose.PASSWORD_RESET, serializer.validated_data["code"])
        if otp is None:
            return Response({"detail": "Invalid or expired reset code."}, status=status.HTTP_400_BAD_REQUEST)

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


class GoogleLoginView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(
        tags=["Auth"],
        summary="Google Login",
        description="Verifies the id_token from Google and logs the user in (or signs them up).",
        request=GoogleLoginSerializer,
        responses={
            200: UserSerializer,
            400: OpenApiResponse(description="Invalid token or missing email")
        }
    )
    def post(self, request):
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests
        from apps.user.serializers import GoogleLoginSerializer

        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["id_token"]

        try:
            # We skip client_id verification here since we might have multiple frontend clients,
            # or you can pass settings.GOOGLE_CLIENT_ID if you want to be strict.
            idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), settings.GOOGLE_CLIENT_ID)
            
            email = idinfo.get("email")
            if not email:
                return Response({"detail": "Email not provided by Google."}, status=status.HTTP_400_BAD_REQUEST)
            
            email = email.lower()
            
            # Log in or create user
            user = User.objects.filter(email=email).first()
            if not user:
                # Create user
                user = User.objects.create_user(
                    email=email,
                    first_name=idinfo.get("given_name", ""),
                    last_name=idinfo.get("family_name", ""),
                    password=User.objects.make_random_password()
                )
                # Mark as verified since Google verified it
                user.is_verified = True
                user.save(update_fields=["is_verified"])
                send_welcome_email_task(str(user.pk))
            elif not user.is_active:
                return Response({"detail": "This account has been deactivated."}, status=status.HTTP_403_FORBIDDEN)
            
            if not user.is_verified:
                # If they had an unverified account, verify it now since they logged in with Google
                user.is_verified = True
                user.save(update_fields=["is_verified"])

            return _issue_session(user)
            
        except ValueError:
            return Response({"detail": "Invalid Google token."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
