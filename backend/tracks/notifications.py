"""In-site notifications: new matches, chat requests and chat messages."""
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


def notify_chat_request(conversation, requester, recipient, at=None):
    text = f"{requester.name} wants to chat with you"
    Notification.objects.create(
        user=recipient,
        kind=Notification.CHAT_REQUEST,
        from_user=requester,
        conversation=conversation,
        text=text,
        created_at=at or timezone.now(),
    )
    email_alerts.maybe_email(recipient, f"{requester.name} wants to chat on Spotafriend", text)


def notify_chat_answer(conversation, responder, requester, accepted, at=None):
    text = (f"{responder.name} accepted your chat request. Say hi!" if accepted
            else f"{responder.name} isn't available to chat right now")
    Notification.objects.create(
        user=requester,
        kind=Notification.CHAT_ANSWER,
        from_user=responder,
        conversation=conversation,
        text=text,
        created_at=at or timezone.now(),
    )


def resolve_chat_request(user, conversation):
    """The request was answered: its notice is read and, if it hadn't shown
    up yet, it shows up now rather than later as a stale prompt."""
    now = timezone.now()
    requests = Notification.objects.filter(user=user, conversation=conversation, kind=Notification.CHAT_REQUEST)
    requests.filter(created_at__gt=now).update(created_at=now)
    requests.update(read=True)


def touch_last_seen(user_id):
    User.objects.filter(pk=user_id).update(last_seen=timezone.now())


def mark_conversation_read(user, conversation):
    """The user is looking at this chat, so its message notices are read."""
    visible(user).filter(conversation=conversation, read=False).update(read=True)


def mark_all_read(user):
    visible(user).filter(read=False).update(read=True)
