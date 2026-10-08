"""One-to-one chat. A chat starts as a request the other person accepts or
declines. The page checks for news every couple of seconds; made-up
listeners accept requests and answer messages on their own after a pause."""
import random
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from . import notifications
from .models import Conversation, Message, MockPlaylist, Notification, Track, UserTrack

BOT_REPLY_DELAY = (1.5, 3.0)  # seconds
BOT_ACCEPT_DELAY = (1.5, 2.5)  # seconds
MAX_MESSAGE_LENGTH = 1000

BOT_FOLLOW_UPS = [
    "Okay we clearly need to swap playlists 😄",
    "What have you had on repeat this week?",
    "Ever been to a concert that changed your taste?",
    "If you could only keep one album forever, which one?",
    "Honestly I'd go to a show with you. Who's on your list?",
    "Haha same. Got any underrated songs I should hear?",
]


class ChatError(Exception):
    pass


def find_conversation(user, other):
    a, b = sorted([user, other], key=lambda u: u.pk)
    return Conversation.objects.filter(user_a=a, user_b=b).first()


def effective_status(conversation):
    if conversation.status_at and conversation.status_at > timezone.now():
        return Conversation.PENDING
    return conversation.status


def can_message(conversation):
    return effective_status(conversation) == Conversation.ACCEPTED


@transaction.atomic
def request_chat(user, other):
    """User asks to chat with other. Returns the conversation, which may
    already exist: an accepted chat just reopens, and asking someone who
    already asked you counts as accepting their request."""
    conversation = find_conversation(user, other)
    if conversation is None:
        a, b = sorted([user, other], key=lambda u: u.pk)
        conversation = Conversation.objects.create(user_a=a, user_b=b, requested_by=user)
    else:
        status = effective_status(conversation)
        if status == Conversation.ACCEPTED:
            return conversation
        if status == Conversation.PENDING:
            if conversation.requested_by_id == other.pk:
                respond(conversation, user, accept=True)
            return conversation  # otherwise still waiting on the other person
        # Declined earlier: ask again.
        conversation.requested_by = user
        conversation.status, conversation.status_at = Conversation.PENDING, None
        conversation.save()

    notifications.notify_chat_request(conversation, requester=user, recipient=other)
    if other.is_bot:
        _bot_accepts(conversation, bot=other, human=user)
    return conversation


def _bot_accepts(conversation, bot, human):
    at = timezone.now() + timedelta(seconds=random.uniform(*BOT_ACCEPT_DELAY))
    conversation.status, conversation.status_at = Conversation.ACCEPTED, at
    conversation.save()
    notifications.notify_chat_answer(conversation, responder=bot, requester=human, accepted=True, at=at)


@transaction.atomic
def respond(conversation, responder, accept):
    """The person who was asked accepts or declines."""
    if responder.pk not in (conversation.user_a_id, conversation.user_b_id):
        raise ChatError("You're not part of this chat")
    if conversation.requested_by_id == responder.pk:
        raise ChatError("You can't answer your own chat request")
    if effective_status(conversation) != Conversation.PENDING:
        raise ChatError("This chat request was already answered")
    conversation.status = Conversation.ACCEPTED if accept else Conversation.DECLINED
    conversation.status_at = timezone.now()
    conversation.save()
    requester = conversation.requested_by
    notifications.resolve_chat_request(responder, conversation)
    notifications.notify_chat_answer(conversation, responder=responder, requester=requester, accepted=accept)
    if accept and requester.is_bot:
        # A made-up listener who asked first opens with a hello.
        _queue_bot_reply(conversation, bot=requester, human=responder)


def other_participant(conversation, user):
    return conversation.user_b if conversation.user_a_id == user.pk else conversation.user_a


def visible_messages(conversation):
    return conversation.messages.filter(created_at__lte=timezone.now())


def bot_is_typing(conversation):
    return conversation.messages.filter(created_at__gt=timezone.now()).exists()


def find_song(user, track_id):
    """{id, name, artists} for a song in the user's own list, else None.
    Details come from the dataset, or from the user's playlist for songs
    the dataset doesn't have."""
    if not UserTrack.objects.filter(user=user, track_id=track_id).exists():
        return None
    row = Track.objects.filter(track_id=track_id).values("track_name", "artists").first()
    if row:
        return {"id": track_id, "name": row["track_name"], "artists": row["artists"].split(";")}
    playlist = MockPlaylist.objects.filter(url=user.playlist_url).first() if user.playlist_url else None
    for item in (playlist.payload["items"] if playlist else []):
        track = item.get("track") or {}
        if track.get("id") == track_id:
            return {"id": track_id, "name": track["name"], "artists": [a["name"] for a in track["artists"]]}
    return None


@transaction.atomic
def send_message(conversation, sender, body, song=None):
    other = other_participant(conversation, sender)
    if song:
        artists = ", ".join(song["artists"])
        body = body or f"🎵 {song['name']} — {artists}"
        if other.is_bot:
            # A shared song always gets its own reaction, so whatever the bot
            # was still "typing" goes out first.
            _deliver_pending_now(conversation)
    message = Message.objects.create(
        conversation=conversation,
        sender=sender,
        body=body,
        song_id=song["id"] if song else None,
        song_name=song["name"] if song else None,
        song_artists=", ".join(song["artists"]) if song else None,
        created_at=timezone.now(),
    )
    notifications.notify_message(message, recipient=other)
    # Quick back-to-back texts share one pending reply.
    if other.is_bot and not bot_is_typing(conversation):
        _queue_bot_reply(conversation, bot=other, human=sender, trigger=message)
    return message


def _deliver_pending_now(conversation):
    now = timezone.now()
    pending = conversation.messages.filter(created_at__gt=now)
    Notification.objects.filter(conversation=conversation, created_at__gt=now).update(created_at=now)
    pending.update(created_at=now)


GREETING_DELAY = 6  # seconds after import


@transaction.atomic
def queue_greeting(bot, human):
    """Have a made-up match ask to chat shortly after the human imports a
    playlist; they say hi once it's accepted. Skipped if the two already
    have a chat."""
    if find_conversation(human, bot) is not None:
        return
    a, b = sorted([human, bot], key=lambda u: u.pk)
    conversation = Conversation.objects.create(user_a=a, user_b=b, requested_by=bot)
    at = timezone.now() + timedelta(seconds=GREETING_DELAY)
    notifications.notify_chat_request(conversation, requester=bot, recipient=human, at=at)


def _queue_bot_reply(conversation, bot, human, delay=None, trigger=None):
    replies_so_far = conversation.messages.filter(sender=bot).count()
    if trigger is not None and trigger.song_id:
        text = _song_reaction(bot, trigger)
    elif replies_so_far == 0:
        text = _opening_line(bot, human)
    else:
        text = BOT_FOLLOW_UPS[(replies_so_far - 1) % len(BOT_FOLLOW_UPS)]
    if delay is None:
        delay = random.uniform(*BOT_REPLY_DELAY)
    message = Message.objects.create(
        conversation=conversation, sender=bot, body=text, created_at=timezone.now() + timedelta(seconds=delay)
    )
    notifications.notify_message(message, recipient=human)


def _song_reaction(bot, message):
    if UserTrack.objects.filter(user=bot, track_id=message.song_id).exists():
        return f"No way, {message.song_name} is on my playlist too! 🙌"
    first_artist = message.song_artists.split(", ")[0]
    return f"Ooh, {message.song_name} by {first_artist}! Adding it to my queue 🎧"


def _artists_of(user):
    track_ids = UserTrack.objects.filter(user=user).values_list("track_id", flat=True)
    return {a for artists in Track.objects.filter(track_id__in=list(track_ids)).values_list("artists", flat=True)
            for a in artists.split(";")}


def _opening_line(bot, human):
    shared = sorted(_artists_of(bot) & _artists_of(human))
    if shared:
        return f"Hey {human.name}! I saw you listen to {shared[0]} too, what's your favorite song of theirs?"
    return f"Hey {human.name}! Our playlists are super similar. What are you listening to lately?"
