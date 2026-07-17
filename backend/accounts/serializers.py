from rest_framework import serializers

from core.models import Organization
from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    """
    Register a new Organization and its first Business Admin.
    """

    organization_name = serializers.CharField(
        max_length=255
    )

    organization_email = serializers.EmailField()

    organization_phone = serializers.CharField(
        max_length=20
    )

    organization_address = serializers.CharField(
        required=False
    )

    password = serializers.CharField(
        write_only=True
    )

    class Meta:
        model = User

        fields = [
            "username",
            "email",
            "password",
            "phone",
            "organization_name",
            "organization_email",
            "organization_phone",
            "organization_address",
        ]

    def create(self, validated_data):

        organization = Organization.objects.create(
            name=validated_data.pop(
                "organization_name"
            ),
            email=validated_data.pop(
                "organization_email"
            ),
            phone=validated_data.pop(
                "organization_phone"
            ),
            address=validated_data.pop(
                "organization_address",
                ""
            ),
        )

        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            phone=validated_data.get(
                "phone",
                ""
            ),
            organization=organization,
            role="ADMIN",
            is_verified=True,
        )

        return user



class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for the logged-in user.
    """

    organization = serializers.StringRelatedField()

    class Meta:
        model = User

        fields = [
            "id",
            "username",
            "email",
            "phone",
            "role",
            "organization",
            "is_verified",
            "created_at",
        ]

        read_only_fields = fields



class StaffSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and managing staff users.
    """

    password = serializers.CharField(
        write_only=True,
        required=False
    )

    class Meta:
        model = User

        fields = [
            "id",
            "username",
            "email",
            "password",
            "phone",
            "is_active",
        ]

        read_only_fields = [
            "id",
        ]


    def create(self, validated_data):
        """
        Create staff user under the logged-in
        Business Admin organization.
        """

        request = self.context["request"]

        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get(
                "email",
                ""
            ),
            password=validated_data["password"],
            phone=validated_data.get(
                "phone",
                ""
            ),
            organization=request.user.organization,
            role="STAFF",
            is_verified=True,
        )

        return user