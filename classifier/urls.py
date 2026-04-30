from django.urls import path
from .views import *

urlpatterns = [
    # path("profiles", profiles_handler),
    # path("profiles/", profiles_handler),

    path("seed", trigger_seed),

    # path("auth/test-login", test_login),

    path("auth/github", github_login),
    path("auth/github/callback", github_callback),

    path("auth/refresh", refresh_token_view),
    path("auth/logout", logout_view),
]