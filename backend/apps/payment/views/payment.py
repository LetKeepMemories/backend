import hashlib
import hmac
import json
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from apps.payment.serializers import (
    InitializePaymentRequestSerializer,
    InitializePaymentResponseSerializer,
    VerifyPaymentRequestSerializer
)

from apps.payment.models import Payment
from apps.payment.services import initialize_payment, verify_payment
from apps.subscription.models import SubscriptionPlan, UserSubscription


class InitializePaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Payments"],
        summary="Initialize Payment",
        description="Initializes a Paystack transaction for the given subscription plan. Returns the Paystack authorization URL and access code.",
        request=InitializePaymentRequestSerializer,
        responses={
            200: InitializePaymentResponseSerializer,
            400: OpenApiResponse(description="Invalid plan or Paystack initialization error")
        }
    )
    def post(self, request):
        plan_id = request.data.get("plan_id")
        plan = get_object_or_404(SubscriptionPlan, id=plan_id, is_active=True)
        
        try:
            data = initialize_payment(user=request.user, subscription_plan=plan)
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class VerifyPaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Payments"],
        summary="Verify Payment",
        description="Verifies a transaction reference with Paystack. On success, it activates the subscription and expires the previous active one.",
        request=VerifyPaymentRequestSerializer,
        responses={
            200: OpenApiResponse(description="Payment successful and subscription activated"),
            400: OpenApiResponse(description="Reference required or payment failed")
        }
    )
    def post(self, request):
        reference = request.data.get("reference")
        if not reference:
            return Response({"detail": "Reference is required."}, status=status.HTTP_400_BAD_REQUEST)

        payment = get_object_or_404(Payment, reference=reference, user=request.user)
        if payment.status == "success":
            return Response({"detail": "Payment already verified."}, status=status.HTTP_200_OK)

        try:
            paystack_data = verify_payment(reference=reference)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if paystack_data.get("status") == "success":
            with transaction.atomic():
                payment.status = "success"
                payment.paid_at = timezone.now()
                payment.save()

                # Activate Subscription
                plan = payment.subscription
                duration = timedelta(days=365) if plan.billing_cycle == "yearly" else timedelta(days=30)
                
                # Deactivate old active subscriptions
                UserSubscription.objects.filter(user=request.user, status="active").update(status="expired")
                
                UserSubscription.objects.create(
                    user=request.user,
                    plan=plan,
                    payment_reference=reference,
                    start_date=timezone.now(),
                    end_date=timezone.now() + duration,
                    status="active"
                )

            return Response({"detail": "Payment successful and subscription activated."}, status=status.HTTP_200_OK)
        else:
            payment.status = "failed"
            payment.save()
            return Response({"detail": "Payment failed."}, status=status.HTTP_400_BAD_REQUEST)


class PaystackWebhookView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Payments"],
        summary="Paystack Webhook",
        description="Receives asynchronous payment events from Paystack (e.g. charge.success) and activates the corresponding subscription. No auth required.",
        responses={200: OpenApiResponse(description="Webhook processed successfully")}
    )
    def post(self, request):
        # Validate signature
        paystack_signature = request.headers.get("x-paystack-signature")
        if not paystack_signature:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        body = request.body
        expected_signature = hmac.new(
            settings.PAYSTACK_SECRET_KEY.encode('utf-8'),
            body,
            hashlib.sha512
        ).hexdigest()

        if expected_signature != paystack_signature:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        event = payload.get("event")
        if event == "charge.success":
            reference = payload["data"]["reference"]
            payment = Payment.objects.filter(reference=reference).first()
            if payment and payment.status != "success":
                with transaction.atomic():
                    payment.status = "success"
                    payment.paid_at = timezone.now()
                    payment.save()

                    plan = payment.subscription
                    duration = timedelta(days=365) if plan.billing_cycle == "yearly" else timedelta(days=30)
                    UserSubscription.objects.filter(user=payment.user, status="active").update(status="expired")
                    UserSubscription.objects.create(
                        user=payment.user,
                        plan=plan,
                        payment_reference=reference,
                        start_date=timezone.now(),
                        end_date=timezone.now() + duration,
                        status="active"
                    )

        return Response(status=status.HTTP_200_OK)
