from django.contrib import admin
from apps.payment.models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["reference", "user", "subscription", "amount", "provider", "status", "created_at"]
    list_filter = ["status", "provider"]
    search_fields = ["reference", "user__email"]
    autocomplete_fields = ["user", "subscription"]
    readonly_fields = ["created_at", "updated_at", "paid_at"]
