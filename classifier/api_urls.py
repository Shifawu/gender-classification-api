from django.urls import path
from . import views

urlpatterns = [
    # user
    path("users/me", views.get_current_user),

    # profiles
    path("profiles", views.get_all_profiles),
    path("profiles/", views.get_all_profiles),

    path("profiles/search", views.search_profiles),

    path("profiles/<uuid:id>", views.get_profile),
    path("profiles/<uuid:id>/delete", views.delete_profile),

    #Seed
    path("seed", views.trigger_seed),
]