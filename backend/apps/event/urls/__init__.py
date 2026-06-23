from django.urls import include, path

app_name = "event"

urlpatterns = [
    path("", include("apps.event.urls.event_type")),
    path("", include("apps.event.urls.occasion")),
    path("", include("apps.event.urls.public")),
]
