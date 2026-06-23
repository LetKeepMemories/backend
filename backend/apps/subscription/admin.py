from django.contrib import admin

from apps.subscription.models import SubscriptionPlan, UserSubscription, AdminSubscriptionConfig


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ["name", "price", "billing_cycle", "max_images_count", "max_video_count", "max_audio_count", "max_storage", "allow_video", "allow_audio_message", "is_active", "is_free"]
    list_filter = ["is_active", "is_free", "billing_cycle", "allow_video", "allow_audio_message"]
    search_fields = ["name"]


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ["user", "plan", "status", "start_date", "end_date"]
    list_filter = ["status", "plan"]
    search_fields = ["user__email", "payment_reference"]
    autocomplete_fields = ["user", "plan"]
    readonly_fields = ["created_at", "updated_at"]

@admin.register(AdminSubscriptionConfig)
class AdminSubscriptionConfigAdmin(admin.ModelAdmin):
    list_display = ["max_images_count", "max_video_count", "max_audio_count", "max_storage", "allow_video", "allow_audio_message", "max_video_size", "max_gallery_images"]

    def has_add_permission(self, request):
        # Prevent creating multiple configurations, as this is a singleton
        if AdminSubscriptionConfig.objects.exists():
            return False
        return super().has_add_permission(request)
