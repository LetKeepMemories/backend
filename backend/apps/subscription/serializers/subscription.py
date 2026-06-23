from rest_framework import serializers

from apps.subscription.models import AdminSubscriptionConfig, SubscriptionPlan, UserSubscription


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
            "is_free",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        is_free = attrs.get('is_free', False)
        # If this is an update, we should check if the instance is already free
        if is_free:
            qs = SubscriptionPlan.objects.filter(is_free=True)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({"is_free": "Another plan is already set as the free plan. Only one plan can be free."})
        return attrs


class AdminSubscriptionConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminSubscriptionConfig
        fields = [
            "id",
            "max_images_count",
            "max_video_count",
            "max_audio_count",
            "max_storage",
            "allow_video",
            "allow_audio_message",
            "max_video_size",
            "max_gallery_images",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GalleryLimitSerializer(serializers.Serializer):
    max_gallery_images = serializers.IntegerField()


class UserSubscriptionSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer()

    class Meta:
        model = UserSubscription
        fields = ["id", "plan", "status", "start_date", "end_date"]
