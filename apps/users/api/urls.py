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
