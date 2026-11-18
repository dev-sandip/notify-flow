from django.urls import path

from .views import (
    NotificationCancelView,
    NotificationDetailView,
    NotificationListCreateView,
)

app_name = "notifications"

urlpatterns = [
    path(
        "",
        NotificationListCreateView.as_view(),
        name="notification-list-create",
    ),
    path(
        "<uuid:id>/",
        NotificationDetailView.as_view(),
        name="notification-detail",
    ),
    path(
        "<uuid:id>/cancel/",
        NotificationCancelView.as_view(),
        name="notification-cancel",
    ),
]
