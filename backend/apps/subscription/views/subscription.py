from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from apps.subscription.models import SubscriptionPlan
from apps.subscription.serializers import SubscriptionPlanSerializer, UserSubscriptionSerializer
from apps.subscription.services import get_active_plan, get_active_subscription


@extend_schema(
    tags=["Subscriptions"],
    summary="List Subscription Plans",
    description="Returns all active pricing plans available for the platform.",
    responses={200: SubscriptionPlanSerializer(many=True)}
)
class SubscriptionPlanListView(generics.ListAPIView):

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = SubscriptionPlanSerializer
    pagination_class = None
    queryset = SubscriptionPlan.objects.filter(is_active=True)


class MySubscriptionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Subscriptions"],
        summary="Get Active Subscription",
        description="Returns the current user's active subscription details. If they don't have one, returns the free tier structure.",
        responses={200: UserSubscriptionSerializer}
    )
    def get(self, request):
        subscription = get_active_subscription(request.user)
        if subscription:
            return Response(UserSubscriptionSerializer(subscription).data)

        plan = get_active_plan(request.user)
        return Response({"id": None, "plan": SubscriptionPlanSerializer(plan).data, "status": "active", "start_date": None, "end_date": None})
