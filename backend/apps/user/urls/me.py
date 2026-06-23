from django.urls import path

from apps.user.views import MeView

urlpatterns = [
    path("me/", MeView.as_view(), name="me"),
]
