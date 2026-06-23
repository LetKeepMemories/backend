from rest_framework import viewsets

from apps.subscription.models import SubscriptionPlan
from apps.subscription.serializers import AdminSubscriptionPlanSerializer
from apps.user.permissions import IsSuperAdminUser


class AdminSubscriptionPlanViewSet(viewsets.ModelViewSet):
    """Admin CRUD for pricing plans."""

    permission_classes = [IsSuperAdminUser]
    serializer_class = AdminSubscriptionPlanSerializer
    queryset = SubscriptionPlan.objects.all().order_by("price")
    pagination_class = None
