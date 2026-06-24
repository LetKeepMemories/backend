import requests
from django.conf import settings
from rest_framework.exceptions import APIException

from apps.payment.models import Payment

class PaystackError(APIException):
    status_code = 400
    default_detail = "Error communicating with Paystack."
    default_code = "paystack_error"


def initialize_payment(*, user, subscription_plan) -> dict:
    url = "https://api.paystack.co/transaction/initialize"
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    # Price is in standard currency units (e.g. NGN/USD), Paystack expects smallest unit (kobo/cents)
    amount_in_smallest_unit = int(subscription_plan.price * 100)
    
    data = {
        "email": user.email,
        "amount": amount_in_smallest_unit,
        "callback_url": f"{settings.FRONTEND_URL}/payment/verify",
        "metadata": {
            "user_id": str(user.id),
            "subscription_plan_id": str(subscription_plan.id)
        }
    }

    response = requests.post(url, json=data, headers=headers)
    if not response.ok:
        try:
            error_msg = response.text
        except Exception:
            error_msg = "Payment gateway configuration error."
        raise PaystackError(f"Paystack initialization failed: {error_msg}")
        
    res_data = response.json()
    if not res_data.get("status"):
        raise PaystackError(res_data.get("message", "Paystack initialization failed."))

    # Store the pending payment
    Payment.objects.create(
        user=user,
        subscription=subscription_plan,
        provider="paystack",
        reference=res_data["data"]["reference"],
        amount=subscription_plan.price,
        status="pending"
    )

    return res_data["data"]


def verify_payment(*, reference: str) -> dict:
    url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
    }

    response = requests.get(url, headers=headers)
    if not response.ok:
        raise PaystackError("Failed to verify transaction with Paystack.")

    res_data = response.json()
    if not res_data.get("status"):
        raise PaystackError(res_data.get("message", "Verification failed."))
        
    return res_data["data"]
