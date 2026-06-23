from django.urls import path
from apps.event.views import EventTypeListView, GalleryLimitView

urlpatterns = [
    path("event-types/", EventTypeListView.as_view(), name="event-types"),
    path("gallery-limit/", GalleryLimitView.as_view(), name="gallery-limit"),
]
