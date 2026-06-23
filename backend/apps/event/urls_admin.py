from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.event.views.admin import AdminEventTypeViewSet, AdminOccasionDetailView, AdminOccasionListView

router = DefaultRouter()
router.register("event-types", AdminEventTypeViewSet, basename="admin-event-type")

urlpatterns = [
    path("occasions/", AdminOccasionListView.as_view(), name="admin-occasions-list"),
    path("occasions/<uuid:id>/", AdminOccasionDetailView.as_view(), name="admin-occasion-detail"),
    path("", include(router.urls)),
]
