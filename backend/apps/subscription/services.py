from django.db.models import Q
from django.utils import timezone

from apps.subscription.models import SubscriptionPlan, UserSubscription

FREE_PLAN_NAME = "Free"


def get_free_plan() -> SubscriptionPlan:
    return SubscriptionPlan.objects.get(name=FREE_PLAN_NAME)


def get_active_subscription(user) -> UserSubscription | None:
    return (
        UserSubscription.objects.filter(user=user, status=UserSubscription.Status.ACTIVE)
        .filter(Q(end_date__isnull=True) | Q(end_date__gte=timezone.now()))
        .select_related("plan")
        .order_by("-start_date")
        .first()
    )


def get_active_plan(user) -> SubscriptionPlan:
    """Every user effectively has a plan — paid subscribers get whatever
    they're actively subscribed to, everyone else falls back to Free.
    """
    subscription = get_active_subscription(user)
    return subscription.plan if subscription else get_free_plan()
