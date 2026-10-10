from django.urls import include, path

from tracks.views import chat_page, index

urlpatterns = [
    path("", index),
    path("chat/", chat_page),
    path("api/", include("tracks.urls")),
]
