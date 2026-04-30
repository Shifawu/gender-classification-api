from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
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

    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]