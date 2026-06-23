from django.db.models import Q
from django.utils import timezone

from apps.subscription.models import AdminSubscriptionConfig, SubscriptionPlan, UserSubscription

def get_free_plan() -> SubscriptionPlan:
    plan = SubscriptionPlan.objects.filter(is_free=True).first()
    if not plan:
        # Fallback if no plan is marked as free yet (should be configured by admin)
        plan, _ = SubscriptionPlan.objects.get_or_create(
            name="Free",
            defaults={"is_free": True, "price": 0}
        )
    return plan


def get_admin_config() -> AdminSubscriptionConfig:
    """Admins don't subscribe to a plan, but their occasions still need
    upload limits — backed by this admin-editable singleton instead."""
    config = AdminSubscriptionConfig.objects.first()
    if config is None:
        config = AdminSubscriptionConfig.objects.create()
    return config


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
