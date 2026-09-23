from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html

from .models import Actor, Genre, Movie


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "movie_count"]
    search_fields = ["name"]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(movie_total=Count("movies"))

    @admin.display(description="Movies", ordering="movie_total")
    def movie_count(self, obj):
        return obj.movie_total


@admin.register(Actor)
class ActorAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "birth_year", "movie_count"]
    search_fields = ["name"]
    list_filter = ["birth_year"]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(movie_total=Count("movies"))

    @admin.display(description="Movies", ordering="movie_total")
    def movie_count(self, obj):
        return obj.movie_total


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ["poster_preview", "id", "title", "year", "genre", "duration", "actor_count"]
    list_display_links = ["title"]
    list_filter = ["genre", "year"]
    search_fields = ["title", "description", "actors__name"]
    ordering = ["-year", "title"]
    autocomplete_fields = ["actors"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("genre").annotate(
            actor_total=Count("actors")
        )

    @admin.display(description="Actors", ordering="actor_total")
    def actor_count(self, obj):
        return obj.actor_total

    @admin.display(description="Preview")
    def poster_preview(self, obj):
        if not obj.img_link:
            return "No image"
        return format_html(
            '<img src="{}" alt="" width="60" height="90" '
            'style="object-fit: cover; border-radius: 6px;">',
            obj.img_link,
        )
