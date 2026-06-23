from rest_framework import generics, viewsets

from apps.event.models import EventType, Occasion
from apps.event.serializers import AdminEventTypeSerializer, AdminOccasionSerializer
from apps.user.permissions import IsSuperAdminUser


class AdminEventTypeViewSet(viewsets.ModelViewSet):
    """Admin CRUD for occasion types (e.g. Birthday, Memorial)."""

    permission_classes = [IsSuperAdminUser]
    serializer_class = AdminEventTypeSerializer
    queryset = EventType.objects.all().order_by("name")
    pagination_class = None


class AdminOccasionListView(generics.ListAPIView):
    """Cross-owner read-only oversight of every occasion on the platform."""

    permission_classes = [IsSuperAdminUser]
    serializer_class = AdminOccasionSerializer

    def get_queryset(self):
        return Occasion.objects.all().select_related("event_type", "owner").order_by("-created_at")


class AdminOccasionDetailView(generics.DestroyAPIView):
    """Lets an admin remove an occasion that violates platform policy."""

    permission_classes = [IsSuperAdminUser]
    serializer_class = AdminOccasionSerializer
    queryset = Occasion.objects.all()
    lookup_field = "id"
