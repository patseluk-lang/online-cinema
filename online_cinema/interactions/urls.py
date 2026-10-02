from django.urls import path

from . import views

urlpatterns = [
    path("favorite/<int:movie_id>/", views.toggle_favorite, name="toggle_favorite"),
    path("watch/<int:movie_id>/", views.watch_movie, name="watch_movie"),
    path("watch/complete/<int:movie_id>/", views.complete_watch, name="complete_watch"),
    path("rate/<int:movie_id>/", views.rate_movie, name="rate_movie"),
    path("comment/<int:movie_id>/", views.add_comment, name="add_comment"),
    path("comment/<int:movie_id>/reply/<int:comment_id>/", views.add_reply, name="add_reply"),
    path("comment/<int:comment_id>/edit/", views.edit_comment, name="edit_comment"),
    path("comment/<int:comment_id>/delete/", views.delete_comment, name="delete_comment"),
]
