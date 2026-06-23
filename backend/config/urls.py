from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from apps.core.views import landing_page, admin_stats

urlpatterns = [
    path("", landing_page, name="landing_page"),
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.user.urls")),
    path("api/subscriptions/", include("apps.subscription.urls")),
    path("api/payments/", include("apps.payment.urls")),
    path("api/", include("apps.event.urls")),
    path("api/admin/stats/", admin_stats, name="admin_stats"),
    path("api/admin/", include("apps.user.urls.admin")),
    path("api/admin/", include("apps.event.urls_admin")),
    path("api/admin/", include("apps.subscription.urls_admin")),
    path("api/admin/", include("apps.payment.urls_admin")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]
