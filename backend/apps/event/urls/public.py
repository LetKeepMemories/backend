from django.urls import path

from apps.event.views import (
    GuestMediaSignatureView,
    GuestMessageCreateView,
    PublicMessageListView,
    PublicOccasionDetailView,
)

urlpatterns = [
    path("public/occasions/<slug:slug>/", PublicOccasionDetailView.as_view(), name="public_occasion_detail"),
    path("public/occasions/<slug:slug>/messages/", PublicMessageListView.as_view(), name="public_message_list"),
    path(
        "public/occasions/<slug:slug>/messages/submit/",
        GuestMessageCreateView.as_view(),
        name="public-message-create",
    ),
    path(
        "public/occasions/<slug:slug>/media-signature/",
        GuestMediaSignatureView.as_view(),
        name="guest-media-signature",
    ),
]
