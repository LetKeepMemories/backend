from django.contrib import admin

from apps.event.models import EventType, Message, MessageMedia, Occasion, OccasionGallery


@admin.register(EventType)
class EventTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


class MessageMediaInline(admin.TabularInline):
    model = MessageMedia
    extra = 0
    readonly_fields = ["created_at"]


class OccasionGalleryInline(admin.TabularInline):
    model = OccasionGallery
    extra = 1
    readonly_fields = ["created_at"]


@admin.register(Occasion)
class OccasionAdmin(admin.ModelAdmin):
    list_display = ["title", "event_type", "owner", "status", "public_url", "created_at"]
    list_filter = ["status", "event_type"]
    search_fields = ["title", "slug", "person_first_name", "person_last_name", "owner__email"]
    autocomplete_fields = ["owner"]
    readonly_fields = ["id", "slug", "public_url", "created_at", "updated_at"]
    inlines = [OccasionGalleryInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["sender_full_name", "occasion", "relationship", "created_at"]
    search_fields = ["sender_first_name", "sender_last_name", "message", "occasion__title"]
    autocomplete_fields = ["occasion"]
    readonly_fields = ["id", "created_at", "updated_at"]
    inlines = [MessageMediaInline]

@admin.register(OccasionGallery)
class OccasionGalleryAdmin(admin.ModelAdmin):
    list_display = ["occasion", "created_at"]
    search_fields = ["occasion__title"]
    autocomplete_fields = ["occasion"]
    readonly_fields = ["created_at", "updated_at"]
