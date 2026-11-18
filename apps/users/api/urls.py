from django.urls import path

from .views import (
    ChangePasswordView,
    LoginView,
    LogoutView,
    MeView,
    RefreshTokenView,
    RegisterView,
)

app_name = "users"
# urlpatterns is a list of URL patterns that define the routing for the user-related API endpoints. Each path function maps a specific URL pattern to a corresponding view class, allowing users to register, log in, refresh tokens, log out, retrieve their profile information, and change their password. The app_name variable is used to namespace the URLs for this app, preventing naming conflicts with other apps in the project.
urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("token/refresh/", RefreshTokenView.as_view(), name="token-refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    path(
        "change-password/",
        ChangePasswordView.as_view(),
        name="change-password",
    ),
]
