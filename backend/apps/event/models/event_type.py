from django.db import models

from apps.core.utils.models import BaseModel
from apps.event.constants import EVENT_TYPE_URL_PREFIXES


class EventType(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def url_prefix(self) -> str:
        return EVENT_TYPE_URL_PREFIXES.get(self.slug, self.slug)
