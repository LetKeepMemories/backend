from django.db import models

from apps.core.utils.models import BaseModel
from apps.subscription.models import SubscriptionPlan
from apps.user.models import User

class Payment(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payments")
    subscription = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True, blank=True, related_name="payments")
    provider = models.CharField(max_length=50)
    reference = models.CharField(max_length=255, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} - {self.amount} ({self.status})"
