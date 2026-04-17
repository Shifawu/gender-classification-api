from django.urls import path
from .views import (
    classify_name,
    create_profile,
    get_profile,
    get_all_profiles,
    delete_profile
)

urlpatterns = [
    path('classify', classify_name),

    # Stage 1
    path('profiles', create_profile),            # POST
    path('profiles', get_all_profiles),         # GET all
    path('profiles/<uuid:id>', get_profile),     # GET one
    path('profiles/<uuid:id>/delete', delete_profile),  # DELETE
]