from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.event.views import (
    MessageModerationView,
    OccasionGalleryUploadView,
    OccasionMessageListView,
    OccasionProfileImageSignatureView,
    OccasionViewSet,
)

router = DefaultRouter()
router.register("occasions", OccasionViewSet, basename="occasion")

urlpatterns = [
    path("occasions/<uuid:id>/gallery/", OccasionGalleryUploadView.as_view(), name="occasion_gallery_upload"),
    path(
        "occasions/profile-image-signature/",
        OccasionProfileImageSignatureView.as_view(),
        name="profile-image-signature",
    ),
    path(
        "occasions/<uuid:occasion_id>/messages/",
        OccasionMessageListView.as_view(),
        name="occasion-messages",
    ),
    path(
        "occasions/<uuid:occasion_id>/messages/<uuid:message_id>/",
        MessageModerationView.as_view(),
        name="message-moderate",
    ),
    path("", include(router.urls)),
]
