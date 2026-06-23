from django.db.models import Sum
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.payment.models import Payment
from apps.payment.serializers import AdminPaymentSerializer
from apps.user.permissions import IsSuperAdminUser


class AdminPaymentListView(generics.ListAPIView):
    """Every payment on the platform, newest first — for the admin
    Revenue & Payments screen."""

    permission_classes = [IsSuperAdminUser]
    serializer_class = AdminPaymentSerializer

    def get_queryset(self):
        return Payment.objects.select_related("user", "subscription").order_by("-created_at")


class AdminRevenueSummaryView(APIView):
    permission_classes = [IsSuperAdminUser]

    def get(self, request):
        payments = Payment.objects.all()
        successful = payments.filter(status="success")
        total_revenue = successful.aggregate(total=Sum("amount"))["total"] or 0

        return Response({
            "total_revenue": total_revenue,
            "successful_count": successful.count(),
            "failed_count": payments.filter(status="failed").count(),
            "pending_count": payments.exclude(status__in=["success", "failed"]).count(),
        })
