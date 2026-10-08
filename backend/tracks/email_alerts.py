"""Email alerts through AWS SNS for people who aren't on the site.

Everything goes through one SNS topic. Each person's email subscription has a
filter, so SNS only delivers messages tagged with that person's alert key.
The key comes from the email address itself, so it stays the same across
server restarts (when user ids get reused).

Set SPOTAFRIEND_EMAIL_ALERTS (in .env or the terminal):
  off (default)  no email alerts
  log            print the emails that would be sent, without calling AWS
  sns            send through AWS SNS, using the usual AWS credentials

In sns mode, SPOTAFRIEND_SNS_TOPIC_ARN points at an existing topic (e.g. one
a teammate created). Without it, a topic named SPOTAFRIEND_SNS_TOPIC is
looked up or created in your own AWS account.
"""
import hashlib
import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from django.utils import timezone

logger = logging.getLogger(__name__)

MODE = os.environ.get("SPOTAFRIEND_EMAIL_ALERTS", "off").lower()
TOPIC_ARN = os.environ.get("SPOTAFRIEND_SNS_TOPIC_ARN")
TOPIC_NAME = os.environ.get("SPOTAFRIEND_SNS_TOPIC", "spotafriend-alerts")
# A topic ARN names its region (arn:aws:sns:<region>:<account>:<name>), and
# SNS only accepts it from a client in that region.
REGION = (os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
          or (TOPIC_ARN.split(":")[3] if TOPIC_ARN and TOPIC_ARN.count(":") >= 5 else None))
SITE_URL = os.environ.get("SPOTAFRIEND_SITE_URL", "http://localhost:8000")
# Someone whose page hasn't checked in for this long counts as away.
AWAY_AFTER = timedelta(seconds=int(os.environ.get("SPOTAFRIEND_AWAY_SECONDS", "60")))

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Sending happens in the background so a slow AWS call never delays a chat message.
_executor = ThreadPoolExecutor(max_workers=2)
_client = None
_topic_arn = None


class EmailAlertError(Exception):
    pass


def available():
    return MODE in ("log", "sns")


def _sns():
    global _client, _topic_arn
    if _client is None:
        import boto3

        _client = boto3.client("sns", region_name=REGION) if REGION else boto3.client("sns")
        # create_topic returns the existing topic if it's already there.
        _topic_arn = TOPIC_ARN or _client.create_topic(Name=TOPIC_NAME)["TopicArn"]
    return _client, _topic_arn


def alert_key(email):
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()[:24]


def _find_subscription(email):
    client, topic_arn = _sns()
    for page in client.get_paginator("list_subscriptions_by_topic").paginate(TopicArn=topic_arn):
        for sub in page["Subscriptions"]:
            if sub["Protocol"] == "email" and sub["Endpoint"].lower() == email.lower():
                return sub
    return None


def status(email):
    """"none", "pending" (waiting for the confirmation click) or "on"."""
    if not email:
        return "none"
    if MODE == "log":
        return "on"
    try:
        sub = _find_subscription(email)
    except Exception as e:
        raise EmailAlertError(f"Couldn't reach AWS SNS: {e}") from e
    if sub is None:
        return "none"
    return "pending" if sub["SubscriptionArn"] == "PendingConfirmation" else "on"


def subscribe(email):
    """Sign an address up. AWS emails a confirmation link the first time."""
    if not EMAIL_PATTERN.match(email):
        raise EmailAlertError("That doesn't look like an email address")
    if MODE == "log":
        print(f"[email-alerts] (log mode) would subscribe {email}")
        return "on"
    current = status(email)
    if current != "none":
        return current
    client, topic_arn = _sns()
    try:
        client.subscribe(
            TopicArn=topic_arn,
            Protocol="email",
            Endpoint=email,
            Attributes={"FilterPolicy": json.dumps({"alert_key": [alert_key(email)]})},
        )
    except Exception as e:
        raise EmailAlertError(f"Couldn't sign up for email alerts: {e}") from e
    return "pending"


def is_away(user):
    return user.last_seen is None or timezone.now() - user.last_seen > AWAY_AFTER


def maybe_email(recipient, subject, text):
    """Email the recipient about something new, if they've opted in and
    aren't currently on the site."""
    if not available() or recipient.is_bot or not recipient.email or not is_away(recipient):
        return
    body = f"{text}\n\nOpen Spotafriend to reply: {SITE_URL}"
    if MODE == "log":
        print(f"[email-alerts] (log mode) would email {recipient.email}: {subject} | {text}")
        return
    _executor.submit(_publish, recipient.email, subject, body)


def _publish(email, subject, body):
    try:
        client, topic_arn = _sns()
        client.publish(
            TopicArn=topic_arn,
            Subject=subject,
            Message=body,
            MessageAttributes={"alert_key": {"DataType": "String", "StringValue": alert_key(email)}},
        )
    except Exception:
        logger.exception("Sending an email alert to %s failed", email)
