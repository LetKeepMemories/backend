from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from apps.event.models import Message
from apps.user.models import User
from apps.user.permissions import IsSuperAdminUser
from apps.user.utils.tasks import send_password_reset_email_task, send_verification_email_task
from apps.subscription.services import get_active_plan


def _serialize_user(user) -> dict:
    plan = get_active_plan(user)
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "user_type": user.user_type,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "date_joined": user.created_at.isoformat(),
        "active_plan": plan.name if plan else "None",
    }


@extend_schema(
    tags=["Admin"],
    summary="List All Users",
    description="Returns a list of all users, their registration dates, and their active subscription plan. Restricted to admins."
)
class AdminUserListView(generics.ListAPIView):
    permission_classes = [IsSuperAdminUser]

    def get(self, request, *args, **kwargs):
        users = User.objects.all().order_by('-created_at')
        return Response({"results": [_serialize_user(user) for user in users]})


class AdminUserDetailView(APIView):
    """Lets an admin inspect a single user's usage (occasions, messages,
    storage), toggle their active status, or remove the account."""

    permission_classes = [IsSuperAdminUser]

    def get_user(self, id):
        return generics.get_object_or_404(User, id=id)

    @extend_schema(
        tags=["Admin"],
        summary="Get User Detail & Usage Stats",
        description="Returns the user's profile plus their occasion/message/storage usage.",
    )
    def get(self, request, id):
        user = self.get_user(id)
        occasions = [
            {
                "id": occasion.id,
                "title": occasion.title,
                "status": occasion.status,
                "message_count": occasion.messages.count(),
                "created_at": occasion.created_at.isoformat(),
            }
            for occasion in user.occasions.all().order_by("-created_at")
        ]
        data = _serialize_user(user)
        data["stats"] = {
            "total_occasions": len(occasions),
            "total_messages": Message.objects.filter(occasion__owner=user).count(),
            "total_storage_bytes": user.media_storage_used_bytes,
        }
        data["occasions"] = occasions
        return Response(data)

    @extend_schema(
        tags=["Admin"],
        summary="Update User Active Status",
        description="Activates or deactivates the user's account.",
        responses={
            200: OpenApiResponse(description="Updated."),
            400: OpenApiResponse(description="Cannot modify your own account this way."),
        },
    )
    def patch(self, request, id):
        user = self.get_user(id)
        if user.id == request.user.id:
            return Response(
                {"detail": "You can't change your own active status here."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        is_active = request.data.get("is_active")
        if is_active is None:
            return Response({"detail": "is_active is required."}, status=status.HTTP_400_BAD_REQUEST)

        user.is_active = bool(is_active)
        user.save(update_fields=["is_active", "updated_at"])
        return Response(_serialize_user(user))

    @extend_schema(
        tags=["Admin"],
        summary="Delete User",
        description="Permanently deletes the user and everything owned by them (occasions, messages, media).",
        responses={
            204: OpenApiResponse(description="Deleted."),
            400: OpenApiResponse(description="Cannot delete your own account."),
        },
    )
    def delete(self, request, id):
        user = self.get_user(id)
        if user.id == request.user.id:
            return Response(
                {"detail": "You can't delete your own account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminUserTriggerPasswordResetView(APIView):
    """Lets an admin send a password reset link to a user on demand,
    e.g. when a guest reports they're locked out."""

    permission_classes = [IsSuperAdminUser]

    @extend_schema(
        tags=["Admin"],
        summary="Trigger Password Reset",
        description="Sends a password reset email to the user.",
        responses={200: OpenApiResponse(description="Reset email sent.")},
    )
    def post(self, request, id):
        user = generics.get_object_or_404(User, id=id)
        send_password_reset_email_task(str(user.pk))
        return Response({"detail": f"Password reset email sent to {user.email}."})


class AdminUserTriggerVerificationView(APIView):
    """Lets an admin resend the verification email for a user whose
    verification is still pending."""

    permission_classes = [IsSuperAdminUser]

    @extend_schema(
        tags=["Admin"],
        summary="Trigger Email Verification",
        description="Resends the verification email if the user isn't verified yet.",
        responses={
            200: OpenApiResponse(description="Verification email sent."),
            400: OpenApiResponse(description="User is already verified."),
        },
    )
    def post(self, request, id):
        user = generics.get_object_or_404(User, id=id)
        if user.is_verified:
            return Response({"detail": "This user is already verified."}, status=status.HTTP_400_BAD_REQUEST)

        send_verification_email_task(str(user.pk))
        return Response({"detail": f"Verification email sent to {user.email}."})
