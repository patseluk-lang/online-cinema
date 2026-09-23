from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from .models import Actor, Genre, Movie

MOVIES_PER_PAGE = 24

SORT_OPTIONS = {
    "newest": ("Newest", ["-year", "title"]),
    "oldest": ("Oldest", ["year", "title"]),
    "shortest": ("Shortest", ["duration", "title"]),
    "longest": ("Longest", ["-duration", "title"]),
}


def movie_list(request):
    query = request.GET.get("q", "").strip()
    genre_id = request.GET.get("genre", "")
    sort = request.GET.get("sort", "")

    movies = Movie.objects.select_related("genre")
    if query:
        movies = movies.filter(title__icontains=query)
    if genre_id.isdigit():
        movies = movies.filter(genre_id=int(genre_id))
    if sort in SORT_OPTIONS:
        movies = movies.order_by(*SORT_OPTIONS[sort][1])
    else:
        sort = ""

    page = Paginator(movies, MOVIES_PER_PAGE).get_page(request.GET.get("page"))

    filters = request.GET.copy()
    filters.pop("page", None)

    return render(request, "movies/movie_list.html", {
        "page": page,
        "genres": Genre.objects.all(),
        "query": query,
        "genre_id": genre_id,
        "sort": sort,
        "sort_options": [(key, label) for key, (label, _) in SORT_OPTIONS.items()],
        "filters": filters.urlencode(),
    })


def movie_detail(request, pk):
    movie = get_object_or_404(
        Movie.objects.select_related("genre").prefetch_related("actors"), pk=pk
    )
    return render(request, "movies/movie_detail.html", {"movie": movie})


def actor_detail(request, pk):
    actor = get_object_or_404(Actor, pk=pk)
    movies = actor.movies.select_related("genre")
    return render(request, "movies/actor_detail.html", {"actor": actor, "movies": movies})
