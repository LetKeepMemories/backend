from django.urls import path
from apps.event.views import EventTypeListView

urlpatterns = [
    path("event-types/", EventTypeListView.as_view(), name="event-types"),
]
