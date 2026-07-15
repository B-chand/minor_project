from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "notification_type",
        "is_read",
        "created_for",
        "organization",
        "created_at",
    )

    list_filter = (
        "notification_type",
        "is_read",
        "organization",
    )

    search_fields = (
        "title",
        "message",
    )