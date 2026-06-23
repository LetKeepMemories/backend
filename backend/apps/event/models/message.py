from django.db import models

from apps.core.utils.models import BaseModel
from apps.event.models.occasion import Occasion


class Message(BaseModel):
    occasion = models.ForeignKey(Occasion, on_delete=models.CASCADE, related_name="messages")

    sender_first_name = models.CharField(max_length=150)
    sender_last_name = models.CharField(max_length=150, blank=True)
    relationship = models.CharField(max_length=100, blank=True)
    message = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["occasion"])]

    def __str__(self):
        return f"{self.sender_first_name} -> {self.occasion.title}"

    @property
    def sender_full_name(self) -> str:
        return f"{self.sender_first_name} {self.sender_last_name}".strip()


class MessageMedia(BaseModel):
    class MediaType(models.TextChoices):
        IMAGE = "IMAGE", "Image"
        VIDEO = "VIDEO", "Video"
        AUDIO = "AUDIO", "Audio"

    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="media")
    media_type = models.CharField(max_length=10, choices=MediaType.choices)

    url = models.URLField()
    thumbnail_url = models.URLField(blank=True)
    file_size = models.PositiveIntegerField(default=0, help_text="Bytes")
    duration = models.FloatField(null=True, blank=True, help_text="Seconds, for audio/video")

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.media_type} for message {self.message_id}"
