from django.urls import path
from .views import profiles_handler, get_profile, delete_profile, search_profiles

urlpatterns = [
    # path("profiles", create_profile),
    # path("profiles/", get_all_profiles),
    path("profiles", profiles_handler),

    path("profiles/search", search_profiles),

    path("profiles/<uuid:id>", get_profile),
    path("profiles/<uuid:id>/delete", delete_profile),
]