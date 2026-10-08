from django.urls import include, path

from tracks.views import index

urlpatterns = [
    path("", index),
    path("api/", include("tracks.urls")),
]
