from django.urls import path

from . import views

urlpatterns = [
    path("favorite/<int:movie_id>/", views.toggle_favorite, name="toggle_favorite"),
]
