from django.urls import path

from apps.subscription.views import MySubscriptionView, SubscriptionPlanListView

urlpatterns = [
    path("plans/", SubscriptionPlanListView.as_view(), name="plans"),
    path("me/", MySubscriptionView.as_view(), name="me"),
]
