from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import F

from apps.event.models import MessageMedia, OccasionGallery

@receiver(post_save, sender=MessageMedia)
def add_message_media_storage(sender, instance, created, **kwargs):
    """When a new message media is uploaded, increment the owner's storage count."""
    if created and instance.file_size:
        owner = instance.message.occasion.owner
        owner.media_storage_used_bytes = F('media_storage_used_bytes') + instance.file_size
        owner.save(update_fields=['media_storage_used_bytes'])

@receiver(post_delete, sender=MessageMedia)
def remove_message_media_storage(sender, instance, **kwargs):
    """When a message media is deleted, decrement the owner's storage count."""
    if instance.file_size:
        owner = instance.message.occasion.owner
        owner.media_storage_used_bytes = F('media_storage_used_bytes') - instance.file_size
        owner.save(update_fields=['media_storage_used_bytes'])

@receiver(post_save, sender=OccasionGallery)
def add_gallery_storage(sender, instance, created, **kwargs):
    """When a gallery image is uploaded, increment the owner's storage count."""
    if created and instance.file_size:
        owner = instance.occasion.owner
        owner.media_storage_used_bytes = F('media_storage_used_bytes') + instance.file_size
        owner.save(update_fields=['media_storage_used_bytes'])

@receiver(post_delete, sender=OccasionGallery)
def remove_gallery_storage(sender, instance, **kwargs):
    """When a gallery image is deleted, decrement the owner's storage count."""
    if instance.file_size:
        owner = instance.occasion.owner
        owner.media_storage_used_bytes = F('media_storage_used_bytes') - instance.file_size
        owner.save(update_fields=['media_storage_used_bytes'])
