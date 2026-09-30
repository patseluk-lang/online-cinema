from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from movies.models import Movie

from .models import Favorite


@login_required
@require_POST
def toggle_favorite(request, movie_id):
    movie = get_object_or_404(Movie, pk=movie_id)

    deleted, _ = Favorite.objects.filter(user=request.user, movie=movie).delete()
    if not deleted:
        Favorite.objects.create(user=request.user, movie=movie)

    return redirect(movie)
