from django.urls import path

from . import views

urlpatterns = [
    path("schema/", views.schema),
    path("query/", views.query),
    path("tracks/", views.track_list),
    path("import/", views.import_playlist),
    path("conversations/", views.start_conversation),
    path("conversations/<int:conversation_id>/messages/", views.conversation_messages),
    path("conversations/<int:conversation_id>/respond/", views.respond_to_chat),
    path("playlists/", views.playlists),
    path("users/", views.users),
    path("users/<int:user_id>/", views.user_detail),
    path("users/<int:user_id>/matches/", views.user_matches),
    path("users/<int:user_id>/notifications/", views.user_notifications),
    path("users/<int:user_id>/email-alerts/", views.user_email_alerts),
]
