"""In-site notifications: new matches and new chat messages."""
from django.utils import timezone

from . import email_alerts
from .models import Notification, User

PREVIEW_LENGTH = 60


def visible(user):
    return Notification.objects.filter(user=user, created_at__lte=timezone.now())


def notify_match(user, match_user, score):
    # Re-importing a playlist replaces the old match notice instead of piling up.
    Notification.objects.filter(user=user, kind=Notification.MATCH).delete()
    Notification.objects.create(
        user=user,
        kind=Notification.MATCH,
        from_user=match_user,
        text=f"You matched with {match_user.name} ({round(score)}%)",
        created_at=timezone.now(),
    )


def notify_message(message, recipient):
    if message.song_id:
        text = f"{message.sender.name} shared a song: {message.song_name}"
    else:
        preview = message.body if len(message.body) <= PREVIEW_LENGTH else message.body[: PREVIEW_LENGTH - 1] + "…"
        text = f"{message.sender.name}: {preview}"
    Notification.objects.create(
        user=recipient,
        kind=Notification.MESSAGE,
        from_user=message.sender,
        conversation=message.conversation,
        text=text,
        created_at=message.created_at,
    )
    email_alerts.maybe_email(recipient, f"New message from {message.sender.name} on Spotafriend", text)


def touch_last_seen(user_id):
    User.objects.filter(pk=user_id).update(last_seen=timezone.now())


def mark_conversation_read(user, conversation):
    """The user is looking at this chat, so its message notices are read."""
    visible(user).filter(conversation=conversation, read=False).update(read=True)


def mark_all_read(user):
    visible(user).filter(read=False).update(read=True)
