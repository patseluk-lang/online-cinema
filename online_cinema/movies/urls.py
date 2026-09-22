from django.urls import path

from . import views

urlpatterns = [
    path("", views.movie_list, name="movie_list"),
    path("movies/<int:pk>/", views.movie_detail, name="movie_detail"),
    path("actors/<int:pk>/", views.actor_detail, name="actor_detail"),
]
