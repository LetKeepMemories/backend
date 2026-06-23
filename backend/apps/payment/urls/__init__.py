from django.urls import include, path

app_name = "payment"

urlpatterns = [
    path("", include("apps.payment.urls.payment")),
]
