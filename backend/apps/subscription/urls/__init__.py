from django.urls import include, path

app_name = "subscription"

urlpatterns = [
    path("", include("apps.subscription.urls.subscription")),
]
