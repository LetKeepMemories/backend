from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from django.conf import settings
from apps.core.utils.cloudinary_utils import generate_upload_signature
from apps.event.models import EventType, Message, MessageMedia, Occasion, OccasionGallery
from apps.event.permissions import IsOccasionOwner
from apps.event.serializers import (
    EventTypeSerializer,
    GuestMessageCreateSerializer,
    MessagePublicSerializer,
    MessageSerializer,
    OccasionCreateSerializer,
    OccasionGallerySerializer,
    OccasionPublicSerializer,
    OccasionSerializer,
    OccasionUpdateSerializer,
)
from apps.event.services import UploadNotAllowed, assert_can_upload_media, create_guest_message, create_occasion
from apps.subscription.serializers import GalleryLimitSerializer
from apps.subscription.services import get_admin_config


@extend_schema(
    tags=["Events (Metadata)"],
    summary="List Event Types",
    description="Returns a list of all active event types (e.g. Birthday, Memorial).",
    responses={200: EventTypeSerializer(many=True)}
)
class EventTypeListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = EventTypeSerializer
    pagination_class = None
    queryset = EventType.objects.filter(is_active=True)


@extend_schema(
    tags=["Events (Metadata)"],
    summary="Get Gallery Image Limit",
    description="Returns the platform-wide max number of gallery images an owner can attach to an occasion, set by admins.",
    responses={200: GalleryLimitSerializer}
)
class GalleryLimitView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        config = get_admin_config()
        return Response({"max_gallery_images": config.max_gallery_images})


@extend_schema(tags=["Events (Owner)"])
class OccasionViewSet(viewsets.ModelViewSet):
    """Owner-facing CRUD for their own occasions."""

    permission_classes = [permissions.IsAuthenticated, IsOccasionOwner]
    lookup_field = "id"

    def get_queryset(self):
        return Occasion.objects.filter(owner=self.request.user).select_related("event_type")

    def get_serializer_class(self):
        if self.action == "create":
            return OccasionCreateSerializer
        if self.action in ("update", "partial_update"):
            return OccasionUpdateSerializer
        return OccasionSerializer

    def perform_create(self, serializer):
        occasion = create_occasion(owner=self.request.user, **serializer.validated_data)
        serializer.instance = occasion

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        output = OccasionSerializer(serializer.instance, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=kwargs.get("partial", False))
        serializer.is_valid(raise_exception=True)
        serializer.save()
        output = OccasionSerializer(instance, context=self.get_serializer_context())
        return Response(output.data)


class OccasionProfileImageSignatureView(APIView):
    """Authenticated owners sign their own occasion's cover/profile image
    upload directly to Cloudinary."""

    @extend_schema(
        tags=["Events (Owner)"],
        summary="Generate Profile Image Signature",
        description="Generates a Cloudinary signature for the owner to upload the occasion profile image.",
        responses={200: OpenApiResponse(description="Signature generated")}
    )
    def post(self, request):
        from apps.subscription.models import AdminSubscriptionConfig
        config = AdminSubscriptionConfig.objects.first()
        max_mb = config.max_upload_image_size_mb if config else 5
        
        estimated_file_size = int(request.data.get("estimated_file_size") or 0)
        if estimated_file_size > max_mb * 1024 * 1024:
            return Response({"detail": f"Image exceeds the maximum size of {max_mb}MB."}, status=status.HTTP_400_BAD_REQUEST)

        signature = generate_upload_signature(folder="occasion_gallery", resource_type="image")
        return Response(signature)

class OccasionGallerySignatureView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsOccasionOwner]

    @extend_schema(
        tags=["Events (Owner)"],
        summary="Generate Gallery Image Signature",
        description="Generates a Cloudinary signature for the owner to upload a gallery image. Enforces storage limits.",
        responses={200: OpenApiResponse(description="Signature generated"), 403: OpenApiResponse(description="Storage limits exceeded")}
    )
    def post(self, request, id):
        occasion = get_object_or_404(Occasion, id=id, owner=request.user)
        estimated_file_size = int(request.data.get("estimated_file_size") or 0)
        try:
            assert_can_upload_media(occasion=occasion, media_type="image", file_size_bytes=estimated_file_size)
        except UploadNotAllowed as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        
        signature = generate_upload_signature(folder=f"occasion_gallery/{occasion.id}", resource_type="image")
        return Response(signature)


class OccasionGalleryUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsOccasionOwner]

    @extend_schema(
        tags=["Events (Owner)"],
        summary="Upload Gallery Image",
        description="Adds a new image to the occasion's gallery. Enforces the admin-configured max gallery image count.",
        responses={
            201: OccasionGallerySerializer,
            400: OpenApiResponse(description="Validation error (gallery image limit reached)")
        }
    )
    def post(self, request, id):
        occasion = get_object_or_404(Occasion, id=id, owner=request.user)

        max_gallery_images = get_admin_config().max_gallery_images
        if occasion.gallery_images.count() >= max_gallery_images:
            return Response(
                {"detail": f"Maximum of {max_gallery_images} images allowed in the gallery."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        image_url = request.data.get("image_url")
        file_size = int(request.data.get("file_size") or 0)
        if not image_url:
            return Response({"detail": "image_url is required."}, status=status.HTTP_400_BAD_REQUEST)

        gallery_image = OccasionGallery.objects.create(occasion=occasion, image_url=image_url, file_size=file_size)
        return Response(OccasionGallerySerializer(gallery_image).data, status=status.HTTP_201_CREATED)


class OccasionGalleryDetailView(generics.DestroyAPIView):
    """Lets an owner remove a single image from their occasion's gallery."""

    permission_classes = [permissions.IsAuthenticated, IsOccasionOwner]
    lookup_url_kwarg = "image_id"

    @extend_schema(
        tags=["Events (Owner)"],
        summary="Delete Gallery Image",
        description="Removes a single image from the occasion's gallery.",
        responses={204: OpenApiResponse(description="Image deleted")}
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)

    def get_queryset(self):
        return OccasionGallery.objects.filter(occasion_id=self.kwargs["id"])


@extend_schema(
    tags=["Events (Owner)"],
    summary="List Occasion Messages",
    description="Returns all messages for a specific occasion owned by the user, including media attachments.",
    responses={200: MessageSerializer(many=True)}
)
class OccasionMessageListView(generics.ListAPIView):
    """Owner's moderation view — every message for one of their occasions,
    published or not."""

    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        occasion = get_object_or_404(Occasion, id=self.kwargs["occasion_id"], owner=self.request.user)
        return occasion.messages.prefetch_related("media")


class MessageModerationView(APIView):
    """Owner toggles visibility or deletes a message left on their occasion."""

    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, occasion_id, message_id):
        return get_object_or_404(
            Message, id=message_id, occasion_id=occasion_id, occasion__owner=self.request.user
        )

    @extend_schema(
        tags=["Events (Owner)"],
        summary="Delete Message",
        description="Allows the owner to permanently delete a message left on their occasion.",
        responses={204: OpenApiResponse(description="Message deleted")}
    )
    def delete(self, request, occasion_id, message_id):
        message = self.get_object(occasion_id, message_id)
        message.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PublicOccasionDetailView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Events (Public)"],
        summary="Get Public Occasion Details",
        description="Retrieves the public details of a published occasion via its unique slug.",
        responses={200: OccasionPublicSerializer}
    )
    def get(self, request, slug):
        occasion = get_object_or_404(Occasion, slug=slug, status=Occasion.Status.PUBLISHED)
        return Response(OccasionPublicSerializer(occasion).data)


@extend_schema(
    tags=["Events (Public)"],
    summary="List Public Messages",
    description="Returns all published messages for an occasion. Note: currently all submitted messages are published instantly.",
    responses={200: MessagePublicSerializer(many=True)}
)
class PublicMessageListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = MessagePublicSerializer

    def get_queryset(self):
        occasion = get_object_or_404(Occasion, slug=self.kwargs["slug"], status=Occasion.Status.PUBLISHED)
        return occasion.messages.prefetch_related("media")


class GuestMessageCreateView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "guest_wish"

    @extend_schema(
        tags=["Events (Public)"],
        summary="Create Guest Message",
        description="Submits a message and its associated media to the public occasion.",
        request=GuestMessageCreateSerializer,
        responses={
            201: MessagePublicSerializer,
            403: OpenApiResponse(description="Upload not allowed (exceeds plan limits)")
        }
    )
    def post(self, request, slug):
        occasion = get_object_or_404(Occasion, slug=slug, status=Occasion.Status.PUBLISHED)
        serializer = GuestMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        media_items = data.pop("media")

        for item in media_items:
            try:
                assert_can_upload_media(
                    occasion=occasion, media_type=item["media_type"], file_size_bytes=item.get("file_size", 0)
                )
            except UploadNotAllowed as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

        message = create_guest_message(occasion=occasion, media_items=media_items, **data)
        return Response(MessagePublicSerializer(message).data, status=status.HTTP_201_CREATED)


class GuestMediaSignatureView(APIView):
    """Issues a signed, direct-to-Cloudinary upload for a guest's photo,
    video, or voice note — checked against the owner's plan before we ever
    hand out a signature, and checked again when the message is submitted.
    """

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "guest_wish"

    @extend_schema(
        tags=["Events (Public)"],
        summary="Generate Guest Media Signature",
        description="Generates a direct-to-Cloudinary upload signature for a guest. Checks storage limits before issuing.",
        responses={
            200: OpenApiResponse(description="Signature generated"),
            403: OpenApiResponse(description="Storage limits exceeded")
        }
    )
    def post(self, request, slug):
        occasion = get_object_or_404(Occasion, slug=slug, status=Occasion.Status.PUBLISHED)
        media_type = request.data.get("media_type")
        if media_type not in MessageMedia.MediaType.values:
            return Response({"detail": "Invalid media_type."}, status=status.HTTP_400_BAD_REQUEST)

        estimated_file_size = int(request.data.get("estimated_file_size") or 0)
        try:
            assert_can_upload_media(occasion=occasion, media_type=media_type, file_size_bytes=estimated_file_size)
        except UploadNotAllowed as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

        resource_type = "video" if media_type in (MessageMedia.MediaType.VIDEO, MessageMedia.MediaType.AUDIO) else "image"
        signature = generate_upload_signature(folder=f"message_media/{occasion.id}", resource_type=resource_type)
        return Response(signature)
