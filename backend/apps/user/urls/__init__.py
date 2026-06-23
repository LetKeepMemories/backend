from django.urls import include, path

app_name = "user"

urlpatterns = [
    path("", include("apps.user.urls.auth")),
    path("", include("apps.user.urls.me")),
]
