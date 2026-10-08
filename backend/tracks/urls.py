from django.urls import path

from . import views

urlpatterns = [
    path("schema/", views.schema),
    path("query/", views.query),
    path("tracks/", views.track_list),
    path("import/", views.import_playlist),
    path("playlists/", views.playlists),
    path("users/", views.users),
    path("users/<int:user_id>/", views.user_detail),
    path("users/<int:user_id>/matches/", views.user_matches),
]
