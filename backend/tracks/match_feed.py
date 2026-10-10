"""Fake-match announcements over AWS SNS -> SQS.

Importing a playlist publishes a MATCH message to the SNS topic
(SPOTAFRIEND_SNS_TOPIC_ARN). The topic fans out to an SQS queue
(SPOTAFRIEND_SQS_QUEUE_URL) that the page polls through /api/match-feed/.
Each message carries the sender's name and the page's client_id, so the page
can tell its own messages from everyone else's.

The feed is off until both settings are set. It needs AWS credentials with
sns:Publish on the topic and sqs:ReceiveMessage / sqs:DeleteMessage on the queue.
"""
import json
import logging
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

TOPIC_ARN = os.environ.get("SPOTAFRIEND_SNS_TOPIC_ARN")
QUEUE_URL = os.environ.get("SPOTAFRIEND_SQS_QUEUE_URL")
SOURCE = "spotafriend"
RECEIVE_MAX = 10


def _region(arn):
    return arn.split(":")[3] if arn and arn.count(":") >= 5 else None


REGION = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or _region(TOPIC_ARN)

# Publishing happens in the background so a slow AWS call never delays an import.
_executor = ThreadPoolExecutor(max_workers=2)
_clients = {}


def available():
    return bool(TOPIC_ARN and QUEUE_URL)


def _client(service):
    if service not in _clients:
        import boto3

        _clients[service] = boto3.client(service, region_name=REGION) if REGION else boto3.client(service)
    return _clients[service]


def build_match(user, match, client_id):
    return {
        "notificationId": str(uuid.uuid4()),
        "type": "MATCH",
        "source": SOURCE,
        "clientId": client_id,
        "fromUserId": user.pk,
        "fromName": user.name,
        "toUserId": match["user_id"],
        "toName": match["name"],
        "score": round(match["score"]),
        "message": f"{user.name} matched with {match['name']}!",
        "sentAt": datetime.now(timezone.utc).isoformat(),
    }


def _publish(notification):
    try:
        _client("sns").publish(
            TopicArn=TOPIC_ARN, Subject="Spotafriend match", Message=json.dumps(notification))
    except Exception:
        logger.exception("Publishing the match notification failed")


def publish_match(user, match, client_id):
    """Queue the fake match for publishing. Returns the notification, or None when the feed is off."""
    if not TOPIC_ARN:
        return None
    notification = build_match(user, match, client_id)
    _executor.submit(_publish, notification)
    return notification


def _unwrap(body):
    """SQS message body -> (notification dict or None, raw text). Handles the
    SNS envelope as well as raw-delivery messages."""
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return None, body
    if isinstance(data, dict) and data.get("Type") == "Notification" and "Message" in data:
        try:
            inner = json.loads(data["Message"])
        except (TypeError, json.JSONDecodeError):
            return None, data["Message"]
        return (inner if isinstance(inner, dict) else None), data["Message"]
    return (data if isinstance(data, dict) else None), body


def poll(client_id):
    """Read what's waiting on the queue, without waiting for more.

    Messages this client_id sent are returned and deleted. Everyone else's are
    returned but left alone (visibility timeout 0), so their own pages still see them."""
    if not QUEUE_URL:
        return []
    sqs = _client("sqs")
    resp = sqs.receive_message(
        QueueUrl=QUEUE_URL, MaxNumberOfMessages=RECEIVE_MAX, VisibilityTimeout=0, WaitTimeSeconds=0)
    out, seen = [], set()
    for msg in resp.get("Messages", []):
        if msg["MessageId"] in seen:  # a short visibility timeout can repeat a message in one batch
            continue
        seen.add(msg["MessageId"])
        notification, raw = _unwrap(msg["Body"])
        mine = bool(client_id and notification
                    and notification.get("source") == SOURCE and notification.get("clientId") == client_id)
        if mine:
            sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=msg["ReceiptHandle"])
        out.append({"mine": mine, "notification": notification, "raw": None if notification else raw})
    return out
