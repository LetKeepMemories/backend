from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.subscription.models import SubscriptionPlan
from apps.subscription.serializers import AdminSubscriptionConfigSerializer, AdminSubscriptionPlanSerializer
from apps.subscription.services import get_admin_config
from apps.user.permissions import IsSuperAdminUser


@extend_schema(tags=["Admin"])
class AdminSubscriptionPlanViewSet(viewsets.ModelViewSet):
    """Admin CRUD for pricing plans."""

    permission_classes = [IsSuperAdminUser]
    serializer_class = AdminSubscriptionPlanSerializer
    queryset = SubscriptionPlan.objects.all().order_by("price")
    pagination_class = None


@extend_schema(tags=["Admin"])
class AdminSubscriptionConfigView(APIView):
    """Singleton settings for the upload limits applied to admin-owned
    occasions, which don't go through a SubscriptionPlan."""

    permission_classes = [IsSuperAdminUser]

    def get(self, request):
        return Response(AdminSubscriptionConfigSerializer(get_admin_config()).data)

    def patch(self, request):
        config = get_admin_config()
        serializer = AdminSubscriptionConfigSerializer(config, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(AdminSubscriptionConfigSerializer(config).data)
