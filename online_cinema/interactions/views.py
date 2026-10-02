from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_GET, require_POST

from movies.models import Movie

from .forms import CommentForm
from .models import Comment, Favorite, Rating, WatchHistory, rating_summary


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


def comments_url(movie):
    return f"{movie.get_absolute_url()}#comments"


@login_required
@require_POST
def add_comment(request, movie_id):
    movie = get_object_or_404(Movie, pk=movie_id)
    form = CommentForm(request.POST)
    if form.is_valid():
        form.instance.user = request.user
        form.instance.movie = movie
        form.save()
    return redirect(comments_url(movie))


@login_required
@require_POST
def add_reply(request, movie_id, comment_id):
    movie = get_object_or_404(Movie, pk=movie_id)
    parent = get_object_or_404(Comment, pk=comment_id, movie=movie)
    form = CommentForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"success": False, "error": "Відповідь не може бути порожньою."}, status=400)

    form.instance.user = request.user
    form.instance.movie = movie
    # Replies stay one level deep: answering a reply attaches to the same top-level comment.
    form.instance.parent = parent.parent or parent
    form.save()
    return JsonResponse({"success": True})


def own_comment_or_error(request, comment_id, action):
    comment = get_object_or_404(Comment, pk=comment_id)
    if comment.user != request.user:
        return None, JsonResponse(
            {"success": False, "error": f"Ви не можете {action} цей коментар."}, status=403
        )
    return comment, None


@login_required
@require_POST
def edit_comment(request, comment_id):
    comment, error = own_comment_or_error(request, comment_id, "редагувати")
    if error:
        return error

    form = CommentForm(request.POST, instance=comment)
    if not form.is_valid():
        return JsonResponse({"success": False, "error": "Коментар не може бути порожнім."}, status=400)

    comment = form.save()
    return JsonResponse({"success": True, "text": comment.text})


@login_required
@require_POST
def delete_comment(request, comment_id):
    comment, error = own_comment_or_error(request, comment_id, "видалити")
    if error:
        return error

    comment.delete()
    return JsonResponse({"success": True})
