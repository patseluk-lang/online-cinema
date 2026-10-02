from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_GET, require_POST

from movies.models import Movie

from .models import Favorite, Rating, WatchHistory, rating_summary


def demo_watch_seconds(movie):
    """Simulated viewing time: one tenth of the runtime in seconds, at least one second."""
    return max(1, round((movie.duration or 0) / 10))


@login_required
@require_POST
def toggle_favorite(request, movie_id):
    movie = get_object_or_404(Movie, pk=movie_id)

    deleted, _ = Favorite.objects.filter(user=request.user, movie=movie).delete()
    if not deleted:
        Favorite.objects.create(user=request.user, movie=movie)

    return redirect(movie)


@login_required
@require_GET
def watch_movie(request, movie_id):
    movie = get_object_or_404(Movie, pk=movie_id)
    return JsonResponse({
        "movie_id": movie.pk,
        "title": movie.title,
        "duration": movie.duration,
        "watch_seconds": demo_watch_seconds(movie),
    })


@login_required
@require_POST
def complete_watch(request, movie_id):
    movie = get_object_or_404(Movie, pk=movie_id)
    WatchHistory.objects.create(
        user=request.user,
        movie=movie,
        watch_duration=demo_watch_seconds(movie),
    )
    return JsonResponse({"success": True, "message": "Фільм додано до історії переглядів"})


@login_required
@require_POST
def rate_movie(request, movie_id):
    movie = get_object_or_404(Movie, pk=movie_id)

    value = request.POST.get("rating", "")
    if not value.isdigit() or not 1 <= int(value) <= 5:
        return JsonResponse(
            {"success": False, "error": "Оцінка повинна бути від 1 до 5."}, status=400
        )

    rating, created = Rating.objects.update_or_create(
        user=request.user, movie=movie, defaults={"value": int(value)}
    )

    return JsonResponse({
        "success": True,
        "value": rating.value,
        "created": created,
        **rating_summary(movie),
    })
