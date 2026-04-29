from django.urls import path
from .views import *

urlpatterns = [
    # path("profiles", profiles_handler),
    # path("profiles/", profiles_handler),

    path("profiles/", get_all_profiles),
    path("profiles", create_profile),

    path("profiles/search", search_profiles),

    path("seed", trigger_seed),

    path("profiles/<uuid:id>", get_profile),
    path("profiles/<uuid:id>", delete_profile),

    path("auth/test-login", test_login),

    path("auth/github", github_login),
    path("auth/github/callback", github_callback),
]