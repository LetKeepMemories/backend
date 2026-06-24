from rest_framework import generics
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from apps.user.models import User
from apps.user.permissions import IsSuperAdminUser
from apps.subscription.services import get_active_plan

@extend_schema(
    tags=["Admin"],
    summary="List All Users",
    description="Returns a list of all users, their registration dates, and their active subscription plan. Restricted to admins."
)
class AdminUserListView(generics.ListAPIView):
    permission_classes = [IsSuperAdminUser]
    
    def get(self, request, *args, **kwargs):
        users = User.objects.all().order_by('-created_at')

        user_data = []
        for user in users:
            plan = get_active_plan(user)
            user_data.append({
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "user_type": user.user_type,
                "date_joined": user.created_at.isoformat(),
                "active_plan": plan.name if plan else "None",
            })
            
        return Response({"results": user_data})
