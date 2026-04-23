from django.urls import path
from .views import *

urlpatterns = [
    path("profiles", profiles_handler),
    path("profiles/", profiles_handler),

    path("profiles/search", search_profiles),

    path("seed", trigger_seed),

    path("profiles/<uuid:id>", get_profile),
    path("profiles/<uuid:id>/delete", delete_profile),
]