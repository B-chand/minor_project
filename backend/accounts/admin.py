from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):

    model = User

    list_display = (
        "username",
        "email",
        "organization",
        "role",
        "is_active",
        "is_staff",
    )

    list_filter = (
        "role",
        "organization",
        "is_active",
    )

    search_fields = (
        "username",
        "email",
        "phone",
    )

    fieldsets = (
        (None, {
            "fields": (
                "username",
                "password",
            )
        }),

        ("Personal Information", {
            "fields": (
                "email",
                "phone",
            )
        }),

        ("Organization", {
            "fields": (
                "organization",
                "role",
            )
        }),

        ("Permissions", {
            "fields": (
                "is_active",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            )
        }),
    )