from django.urls import path
from apps.payment.views import InitializePaymentView, PaystackWebhookView, VerifyPaymentView

urlpatterns = [
    path("initialize/", InitializePaymentView.as_view(), name="initialize_payment"),
    path("verify/", VerifyPaymentView.as_view(), name="verify_payment"),
    path("webhook/", PaystackWebhookView.as_view(), name="paystack_webhook"),
]
