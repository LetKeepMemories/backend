from django.db.models import Sum

from apps.event.models import Message, MessageMedia, Occasion
from apps.event.utils import build_slug_base, generate_unique_slug
from apps.subscription.services import get_active_plan

BYTES_PER_MB = 1024 * 1024


class UploadNotAllowed(Exception):
    """Raised when a media upload would exceed the owner's plan limits."""


def create_occasion(*, owner, event_type, title, person_first_name, person_last_name, slug=None, **extra_fields) -> Occasion:
    if not slug:
        slug_base = build_slug_base(
            event_type_slug=event_type.slug, first_name=person_first_name, last_name=person_last_name
        )
        slug = generate_unique_slug(Occasion, slug_base)
    
    return Occasion.objects.create(
        owner=owner,
        event_type=event_type,
        title=title,
        slug=slug,
        person_first_name=person_first_name,
        person_last_name=person_last_name,
        **extra_fields,
    )


def assert_can_upload_media(*, occasion: Occasion, media_type: str, file_size_bytes: int) -> None:
    """Server-side enforcement of the owner's subscription limits. The
    Cloudinary signature endpoint checks this before issuing a signature,
    and the MessageMedia creation endpoint checks it again afterwards —
    never trust the client's claimed file size/type alone.
    """
    plan = get_active_plan(occasion.owner)

    if media_type == MessageMedia.MediaType.VIDEO and not plan.allow_video:
        raise UploadNotAllowed("Video uploads are not available on the current plan.")
    if media_type == MessageMedia.MediaType.AUDIO and not plan.allow_audio_message:
        raise UploadNotAllowed("Audio messages are not available on the current plan.")
    if media_type == MessageMedia.MediaType.VIDEO and plan.max_video_size:
        if file_size_bytes > plan.max_video_size * BYTES_PER_MB:
            raise UploadNotAllowed("This video exceeds the maximum size allowed on the current plan.")

    if media_type == MessageMedia.MediaType.IMAGE and plan.max_images_count:
        existing_images = MessageMedia.objects.filter(
            message__occasion=occasion, media_type=MessageMedia.MediaType.IMAGE
        ).count()
        if existing_images >= plan.max_images_count:
            raise UploadNotAllowed("This occasion has reached its image limit on the current plan.")

    if media_type == MessageMedia.MediaType.AUDIO and plan.max_audio_count:
        existing_audio = MessageMedia.objects.filter(
            message__occasion=occasion, media_type=MessageMedia.MediaType.AUDIO
        ).count()
        if existing_audio >= plan.max_audio_count:
            raise UploadNotAllowed("This occasion has reached its audio limit on the current plan.")

    if media_type == MessageMedia.MediaType.VIDEO and plan.max_video_count:
        existing_videos = MessageMedia.objects.filter(
            message__occasion=occasion, media_type=MessageMedia.MediaType.VIDEO
        ).count()
        if existing_videos >= plan.max_video_count:
            raise UploadNotAllowed("This occasion has reached its video limit on the current plan.")

    if plan.max_storage:
        total_bytes = (
            MessageMedia.objects.filter(message__occasion__owner=occasion.owner).aggregate(total=Sum("file_size"))[
                "total"
            ]
            or 0
        )
        if total_bytes + file_size_bytes > plan.max_storage * BYTES_PER_MB:
            raise UploadNotAllowed("Storage limit reached on the current plan.")


def create_guest_message(*, occasion: Occasion, media_items: list[dict], **fields) -> Message:
    message = Message.objects.create(occasion=occasion, **fields)
    for item in media_items:
        MessageMedia.objects.create(message=message, **item)

    return message
