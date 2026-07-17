from rest_framework.permissions import BasePermission


class IsSuperAdmin(BasePermission):
    """
    Allows access only to Super Admin users.
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == "SUPER_ADMIN"
        )


class IsBusinessAdmin(BasePermission):
    """
    Allows access only to Business Admin users.
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == "ADMIN"
        )


class IsStaff(BasePermission):
    """
    Allows access only to Staff users.
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == "STAFF"
        )


class IsOrganizationMember(BasePermission):
    """
    Allows any authenticated user belonging
    to an organization.
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.organization is not None
        )
class IsAdminOrSuperAdmin(BasePermission):
    """
    Allows access to Super Admin and Business Admin users.
    """

    def has_permission(self, request, view):

        return (
            request.user.is_authenticated
            and request.user.role in [
                "SUPER_ADMIN",
                "ADMIN",
            ]
        )