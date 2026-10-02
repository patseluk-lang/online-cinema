from django.urls import path

from . import views

urlpatterns = [
    path("favorite/<int:movie_id>/", views.toggle_favorite, name="toggle_favorite"),
    path("watch/<int:movie_id>/", views.watch_movie, name="watch_movie"),
    path("watch/complete/<int:movie_id>/", views.complete_watch, name="complete_watch"),
    path("rate/<int:movie_id>/", views.rate_movie, name="rate_movie"),
]
