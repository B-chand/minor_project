from .models import Notification


def create_notification(
    organization,
    user,
    title,
    message,
    notification_type="SYSTEM"
):
    return Notification.objects.create(
        organization=organization,
        created_for=user,
        title=title,
        message=message,
        notification_type=notification_type,
    )