from django.contrib import admin

from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):

    list_display = (
        "first_name",
        "last_name",
        "phone",
        "email",
        "organization",
        "is_active",
        "created_at",
    )

    list_filter = (
        "organization",
        "is_active",
    )

    search_fields = (
        "first_name",
        "last_name",
        "phone",
        "email",
    )