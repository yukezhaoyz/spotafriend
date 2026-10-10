import os
import time

from django.core.management.base import BaseCommand, CommandError

from tracks import chat_feed

API_KEY_DAYS = 364  # AppSync allows at most 365


class Command(BaseCommand):
    help = ("Create (or reuse) the AppSync Event API that live chat runs on, plus a fresh API key, "
            "and print the settings to paste into .env. Uses the AWS login from `aws configure`.")

    def add_arguments(self, parser):
        parser.add_argument("--name", default="spotafriend-chat", help="Event API name (reused if it exists)")
        parser.add_argument("--region", default=os.environ.get("AWS_REGION") or None,
                            help="AWS region (default: AWS_REGION, then ~/.aws/config)")

    def handle(self, *args, name, region, **options):
        import boto3

        client = boto3.client("appsync", region_name=region) if region else boto3.client("appsync")
        api_key_mode = [{"authType": "API_KEY"}]
        try:
            api = self._find_api(client, name)
            if api:
                self.stdout.write(f"Reusing Event API {name} ({api['apiId']})")
            else:
                api = client.create_api(name=name, eventConfig={
                    "authProviders": api_key_mode,
                    "connectionAuthModes": api_key_mode,
                    "defaultPublishAuthModes": api_key_mode,
                    "defaultSubscribeAuthModes": api_key_mode,
                })["api"]
                self.stdout.write(f"Created Event API {name} ({api['apiId']})")

            namespaces = client.list_channel_namespaces(apiId=api["apiId"])["channelNamespaces"]
            if not any(ns["name"] == chat_feed.NAMESPACE for ns in namespaces):
                client.create_channel_namespace(apiId=api["apiId"], name=chat_feed.NAMESPACE)
                self.stdout.write(f"Created channel namespace {chat_feed.NAMESPACE}")

            key = client.create_api_key(
                apiId=api["apiId"], description="Spotafriend live chat",
                expires=int(time.time()) + API_KEY_DAYS * 86400)["apiKey"]
        except Exception as e:
            raise CommandError(f"AppSync setup failed: {e}") from e

        self.stdout.write("\nAdd these lines to .env (both people's, if you run two copies), then restart the server:\n")
        self.stdout.write(f"SPOTAFRIEND_APPSYNC_HTTP_DOMAIN={api['dns']['HTTP']}")
        self.stdout.write(f"SPOTAFRIEND_APPSYNC_REALTIME_DOMAIN={api['dns']['REALTIME']}")
        self.stdout.write(f"SPOTAFRIEND_APPSYNC_API_KEY={key['id']}")

    def _find_api(self, client, name):
        for page in client.get_paginator("list_apis").paginate():
            for api in page["apis"]:
                if api["name"] == name:
                    return api
        return None
