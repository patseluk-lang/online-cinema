from django.contrib import admin

from .models import Actor, Genre, Movie


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(Actor)
class ActorAdmin(admin.ModelAdmin):
    list_display = ["name", "birth_year"]
    search_fields = ["name"]


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ["title", "year", "genre", "duration"]
    list_filter = ["genre", "year"]
    search_fields = ["title", "description"]
    autocomplete_fields = ["actors"]
