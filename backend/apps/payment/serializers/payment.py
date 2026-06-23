from rest_framework import serializers

from apps.payment.models import Payment


class AdminPaymentSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    plan_name = serializers.CharField(source="subscription.name", read_only=True, default=None)

    class Meta:
        model = Payment
        fields = [
            "id",
            "user_email",
            "user_name",
            "plan_name",
            "provider",
            "reference",
            "amount",
            "status",
            "paid_at",
            "created_at",
        ]


class InitializePaymentRequestSerializer(serializers.Serializer):
    plan_id = serializers.UUIDField(help_text="The ID of the SubscriptionPlan to purchase.")

class InitializePaymentResponseSerializer(serializers.Serializer):
    authorization_url = serializers.URLField()
    access_code = serializers.CharField()
    reference = serializers.CharField()

class VerifyPaymentRequestSerializer(serializers.Serializer):
    reference = serializers.CharField(help_text="The Paystack reference code.")
