from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from apps.core.utils.models import BaseModel
from apps.user.managers import UserManager


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    class UserType(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"

    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    user_type = models.CharField(max_length=20, choices=UserType.choices, default=UserType.OWNER)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
