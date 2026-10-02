from django.contrib import admin

from .models import Comment, Favorite, Rating, WatchHistory


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ["user", "movie", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["user__username", "movie__title"]
    list_select_related = ["user", "movie"]


@admin.register(WatchHistory)
class WatchHistoryAdmin(admin.ModelAdmin):
    list_display = ["user", "movie", "watched_at", "watch_duration"]
    list_filter = ["watched_at"]
    search_fields = ["user__username", "movie__title"]
    list_select_related = ["user", "movie"]


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ["user", "movie", "value", "created_at", "updated_at"]
    list_filter = ["value", "created_at"]
    search_fields = ["user__username", "movie__title"]
    list_select_related = ["user", "movie"]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["user", "movie", "parent", "text_preview", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["user__username", "movie__title", "text"]
    list_select_related = ["user", "movie", "parent__user"]
    raw_id_fields = ["parent"]

    @admin.display(description="Коментар")
    def text_preview(self, obj):
        return obj.text[:30]
