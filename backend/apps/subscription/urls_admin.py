from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.subscription.views.admin import AdminSubscriptionConfigView, AdminSubscriptionPlanViewSet

router = DefaultRouter()
router.register("plans", AdminSubscriptionPlanViewSet, basename="admin-subscription-plan")

urlpatterns = [
    path("config/", AdminSubscriptionConfigView.as_view(), name="admin-subscription-config"),
    path("", include(router.urls)),
]
