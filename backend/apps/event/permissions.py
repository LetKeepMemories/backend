from rest_framework.permissions import BasePermission


class IsOccasionOwner(BasePermission):
    """Object-level permission for Occasion (has .owner) and Message
    (has .occasion.owner) instances alike."""

    def has_object_permission(self, request, view, obj):
        owner = getattr(obj, "owner", None) or obj.occasion.owner
        return owner == request.user
