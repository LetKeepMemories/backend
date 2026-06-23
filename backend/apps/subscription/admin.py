from django.contrib import admin

from apps.subscription.models import SubscriptionPlan, UserSubscription


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ["name", "price", "billing_cycle", "max_images_count", "max_video_count", "max_audio_count", "max_storage", "allow_video", "allow_audio_message", "is_active"]
    list_filter = ["is_active", "billing_cycle", "allow_video", "allow_audio_message"]
    search_fields = ["name"]


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ["user", "plan", "status", "start_date", "end_date"]
    list_filter = ["status", "plan"]
    search_fields = ["user__email", "payment_reference"]
    autocomplete_fields = ["user", "plan"]
    readonly_fields = ["created_at", "updated_at"]
