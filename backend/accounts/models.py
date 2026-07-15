import uuid

from django.db import models
from django.contrib.auth.models import AbstractUser

from core.models import Organization, BaseModel
from .managers import UserManager


class User(AbstractUser, BaseModel):

    ROLE_CHOICES = (
        ("SUPER_ADMIN", "Super Admin"),
        ("ADMIN", "Business Admin"),
        ("STAFF", "Staff"),
    )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="users",
        null=True,
        blank=True
    )

    phone = models.CharField(
        max_length=20,
        blank=True
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="STAFF"
    )

    is_verified = models.BooleanField(default=False)

    objects = UserManager()

    def __str__(self):
        return f"{self.username} ({self.organization})"