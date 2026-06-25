from django.utils.text import slugify
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from apps.event.models import EventType, Message, MessageMedia, Occasion, OccasionGallery


class EventTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventType
        fields = ["id", "name", "slug", "description"]


class AdminEventTypeSerializer(serializers.ModelSerializer):
    """Admin-facing — exposes is_active for management; slug is optional
    and auto-derived from name when left blank."""

    slug = serializers.SlugField(required=False, allow_blank=True)

    class Meta:
        model = EventType
        fields = ["id", "name", "slug", "description", "is_active"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        if not validated_data.get("slug"):
            validated_data["slug"] = slugify(validated_data["name"])
        return super().create(validated_data)


class AdminOccasionSerializer(serializers.ModelSerializer):
    """Cross-owner occasion oversight — used on the admin "All Occasions"
    screen, so it surfaces who owns each occasion."""

    event_type = EventTypeSerializer(read_only=True)
    person_full_name = serializers.CharField(read_only=True)
    message_count = serializers.IntegerField(read_only=True, source="messages.count")
    owner_email = serializers.EmailField(source="owner.email", read_only=True)
    owner_name = serializers.CharField(source="owner.full_name", read_only=True)

    class Meta:
        model = Occasion
        fields = [
            "id",
            "title",
            "slug",
            "public_url",
            "status",
            "event_type",
            "person_full_name",
            "message_count",
            "owner_email",
            "owner_name",
            "created_at",
        ]


class MessageMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageMedia
        fields = ["id", "media_type", "url", "thumbnail_url", "file_size", "duration", "created_at"]
        read_only_fields = ["id", "created_at"]


class OccasionGallerySerializer(serializers.ModelSerializer):
    class Meta:
        model = OccasionGallery
        fields = ["id", "image_url", "created_at"]
        read_only_fields = ["id", "created_at"]


class OccasionSerializer(serializers.ModelSerializer):
    """Owner-facing representation — includes everything, used on the
    dashboard where the owner manages their own occasion."""

    event_type = EventTypeSerializer(read_only=True)
    person_full_name = serializers.CharField(read_only=True)
    message_count = serializers.IntegerField(read_only=True, source="messages.count")
    gallery_images = OccasionGallerySerializer(many=True, read_only=True)

    class Meta:
        model = Occasion
        fields = [
            "id",
            "event_type",
            "title",
            "slug",
            "public_url",
            "status",
            "person_first_name",
            "person_last_name",
            "person_full_name",
            "description",
            "bio",
            "profile_image",
            "event_date",
            "birth_date",
            "death_date",
            "age",
            "metadata",
            "message_count",
            "gallery_images",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "slug", "public_url", "created_at", "updated_at"]


class OccasionCreateSerializer(serializers.ModelSerializer):
    event_type = serializers.SlugRelatedField(slug_field="slug", queryset=EventType.objects.filter(is_active=True))
    slug = serializers.SlugField(
        max_length=255, 
        required=False, 
        allow_blank=True,
        validators=[UniqueValidator(queryset=Occasion.objects.all(), message="This custom URL is already in use. Please choose another.")]
    )

    class Meta:
        model = Occasion
        fields = [
            "event_type",
            "title",
            "slug",
            "status",
            "person_first_name",
            "person_last_name",
            "description",
            "bio",
            "profile_image",
            "event_date",
            "birth_date",
            "death_date",
            "age",
            "metadata",
        ]


class OccasionUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Occasion
        fields = [
            "title",
            "status",
            "description",
            "bio",
            "profile_image",
            "event_date",
            "birth_date",
            "death_date",
            "age",
            "metadata",
        ]


class OccasionPublicSerializer(serializers.ModelSerializer):
    """What a guest sees when they open the public occasion link."""

    event_type = EventTypeSerializer(read_only=True)
    person_full_name = serializers.CharField(read_only=True)
    gallery_images = OccasionGallerySerializer(many=True, read_only=True)
    capabilities = serializers.SerializerMethodField()

    class Meta:
        model = Occasion
        fields = [
            "id",
            "event_type",
            "title",
            "slug",
            "public_url",
            "person_first_name",
            "person_last_name",
            "person_full_name",
            "description",
            "bio",
            "profile_image",
            "event_date",
            "birth_date",
            "death_date",
            "age",
            "metadata",
            "gallery_images",
            "capabilities",
        ]

    def get_capabilities(self, obj):
        from apps.subscription.services import get_active_plan, get_admin_config
        from apps.subscription.models import AdminSubscriptionConfig
        
        plan = get_admin_config() if obj.owner.user_type == "admin" else get_active_plan(obj.owner)
        config = AdminSubscriptionConfig.objects.first()
        
        return {
            "allow_video": plan.allow_video,
            "allow_audio_message": plan.allow_audio_message,
            "max_images_per_message": config.max_images_per_message if config else 5,
            "max_videos_per_message": config.max_videos_per_message if config else 1,
            "max_audio_per_message": config.max_audio_per_message if config else 1,
            "max_upload_image_size_mb": config.max_upload_image_size_mb if config else 5,
            "max_upload_video_size_mb": config.max_upload_video_size_mb if config else 50,
            "max_upload_audio_size_mb": config.max_upload_audio_size_mb if config else 10,
        }


class MessageSerializer(serializers.ModelSerializer):
    """Owner-facing — used on the moderation/manage screen."""

    media = MessageMediaSerializer(many=True, read_only=True)
    sender_full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Message
        fields = [
            "id",
            "sender_first_name",
            "sender_last_name",
            "sender_full_name",
            "relationship",
            "message",
            "is_hidden",
            "media",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class MessagePublicSerializer(serializers.ModelSerializer):
    """What guests see on the public wall — only ever published messages."""

    media = MessageMediaSerializer(many=True, read_only=True)
    sender_full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Message
        fields = [
            "id",
            "sender_full_name",
            "relationship",
            "message",
            "media",
            "created_at",
        ]


class GuestMediaItemSerializer(serializers.Serializer):
    media_type = serializers.ChoiceField(choices=MessageMedia.MediaType.choices)
    url = serializers.URLField()
    thumbnail_url = serializers.URLField(required=False, allow_blank=True)
    file_size = serializers.IntegerField(min_value=0, default=0)
    duration = serializers.FloatField(required=False, allow_null=True)


class GuestMessageCreateSerializer(serializers.Serializer):
    sender_first_name = serializers.CharField(max_length=150)
    sender_last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    relationship = serializers.CharField(max_length=100, required=False, allow_blank=True)
    message = serializers.CharField(allow_blank=True, required=False)
    media = GuestMediaItemSerializer(many=True, required=False, default=list)

    def validate(self, attrs):
        if not attrs.get("message") and not attrs.get("media"):
            raise serializers.ValidationError("Write a message or attach at least one photo, video, or voice note.")
            
        media_items = attrs.get("media", [])
        if media_items:
            from apps.subscription.models import AdminSubscriptionConfig
            config = AdminSubscriptionConfig.objects.first()
            if config:
                image_count = sum(1 for item in media_items if item["media_type"] == "image")
                video_count = sum(1 for item in media_items if item["media_type"] == "video")
                audio_count = sum(1 for item in media_items if item["media_type"] == "audio")
                
                if image_count > config.max_images_per_message:
                    raise serializers.ValidationError(f"Maximum of {config.max_images_per_message} images allowed per message.")
                if video_count > config.max_videos_per_message:
                    raise serializers.ValidationError(f"Maximum of {config.max_videos_per_message} video allowed per message.")
                if audio_count > config.max_audio_per_message:
                    raise serializers.ValidationError(f"Maximum of {config.max_audio_per_message} audio allowed per message.")
        
        return attrs
