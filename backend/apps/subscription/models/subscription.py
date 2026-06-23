from django.db import models

from apps.core.utils.models import BaseModel
from apps.user.models import User

class SubscriptionPlan(BaseModel):
    class BillingCycle(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        YEARLY = "yearly", "Yearly"

    name = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    billing_cycle = models.CharField(max_length=20, choices=BillingCycle.choices, default=BillingCycle.MONTHLY)

    max_images_count = models.PositiveIntegerField(default=50, help_text="Max images per occasion.")
    max_video_count = models.PositiveIntegerField(default=0, help_text="Max videos per occasion.")
    max_audio_count = models.PositiveIntegerField(default=0, help_text="Max audio uploads per occasion.")
    max_storage = models.PositiveIntegerField(help_text="Total storage allowance in MB, across all occasions.")
    allow_video = models.BooleanField(default=False)
    allow_audio_message = models.BooleanField(default=False)
    max_video_size = models.PositiveIntegerField(default=0, help_text="Max size per video upload, in MB.")

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["price"]

    def __str__(self):
        return self.name


class UserSubscription(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name="subscriptions")
    payment_reference = models.CharField(max_length=255, blank=True)

    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        ordering = ["-start_date"]
        indexes = [models.Index(fields=["user", "status"])]

    def __str__(self):
        return f"{self.user.email} - {self.plan.name} ({self.status})"
