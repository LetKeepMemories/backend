from rest_framework import permissions


class IsSuperAdminUser(permissions.BasePermission):
    """Restricts access to users with user_type == "admin" — currently only
    ever set together with is_staff/is_superuser via createsuperuser."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.user_type == "admin")
