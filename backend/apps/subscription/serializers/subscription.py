from rest_framework import serializers

from apps.subscription.models import SubscriptionPlan, UserSubscription


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = [
            "id",
            "name",
            "price",
            "billing_cycle",
            "max_images_count",
            "max_video_count",
            "max_audio_count",
            "max_storage",
            "allow_video",
            "allow_audio_message",
            "max_video_size",
        ]


class AdminSubscriptionPlanSerializer(serializers.ModelSerializer):
    """Admin CRUD — exposes is_active alongside every other plan field."""

    class Meta:
        model = SubscriptionPlan
        fields = [
            "id",
            "name",
            "price",
            "billing_cycle",
            "max_images_count",
            "max_video_count",
            "max_audio_count",
            "max_storage",
            "allow_video",
            "allow_audio_message",
            "max_video_size",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class UserSubscriptionSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer()

    class Meta:
        model = UserSubscription
        fields = ["id", "plan", "status", "start_date", "end_date"]
