from django.urls import path

from apps.payment.views.admin import AdminPaymentListView, AdminRevenueSummaryView

urlpatterns = [
    path("payments/", AdminPaymentListView.as_view(), name="admin-payments-list"),
    path("revenue/", AdminRevenueSummaryView.as_view(), name="admin-revenue-summary"),
]
