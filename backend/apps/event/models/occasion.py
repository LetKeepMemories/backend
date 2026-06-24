from django.db import models

from apps.core.utils.models import BaseModel
from apps.event.models.event_type import EventType
from apps.user.models import User


class Occasion(BaseModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"
        CANCELLED = "cancelled", "Cancelled"

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="occasions")
    event_type = models.ForeignKey(EventType, on_delete=models.PROTECT, related_name="occasions")

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    public_url = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PUBLISHED)

    person_first_name = models.CharField(max_length=150)
    person_last_name = models.CharField(max_length=150, blank=True)

    description = models.TextField(blank=True)
    bio = models.TextField(blank=True)
    profile_image = models.URLField(blank=True)

    event_date = models.DateField(null=True, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    death_date = models.DateField(null=True, blank=True)
    age = models.PositiveIntegerField(null=True, blank=True)

    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["event_type", "slug"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.public_url = f"/{self.event_type.url_prefix}/{self.slug}"
        super().save(*args, **kwargs)

    @property
    def person_full_name(self) -> str:
        return f"{self.person_first_name} {self.person_last_name}".strip()


class OccasionGallery(BaseModel):
    occasion = models.ForeignKey(Occasion, on_delete=models.CASCADE, related_name="gallery_images")
    image_url = models.URLField()
    file_size = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Gallery Image for {self.occasion.title}"
