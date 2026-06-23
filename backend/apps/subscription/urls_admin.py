from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.subscription.views.admin import AdminSubscriptionPlanViewSet

router = DefaultRouter()
router.register("plans", AdminSubscriptionPlanViewSet, basename="admin-subscription-plan")

urlpatterns = [
    path("", include(router.urls)),
]
