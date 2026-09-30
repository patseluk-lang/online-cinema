from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import RegisterForm


def safe_next_url(request):
    """Return the ?next= address if it points to this site, otherwise None."""
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return next_url
    return None


def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("login")
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    error = None

    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username"),
            password=request.POST.get("password"),
        )
        if user is not None:
            login(request, user)
            return redirect(safe_next_url(request) or "movie_list")
        error = "Неправильний логін або пароль."

    return render(request, "accounts/login.html", {
        "error": error,
        "next": safe_next_url(request) or "",
    })


@require_POST
def logout_view(request):
    logout(request)
    return redirect("movie_list")


@login_required
def profile(request):
    favorites = request.user.favorites.select_related("movie__genre").order_by("-created_at")
    return render(request, "accounts/profile.html", {"favorites": favorites})
