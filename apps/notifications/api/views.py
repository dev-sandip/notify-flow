from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.models import Notification, NotificationStatus

from .serializers import (
    NotificationCreateSerializer,
    NotificationSerializer,
)


class NotificationListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).prefetch_related(
            "delivery_attempts"
        )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return NotificationCreateSerializer

        return NotificationSerializer


class NotificationDetailView(generics.RetrieveAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).prefetch_related(
            "delivery_attempts"
        )


class NotificationCancelView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id):
        try:
            notification = Notification.objects.get(
                id=id,
                user=request.user,
            )
        except Notification.DoesNotExist:
            return Response(
                {"detail": "Notification not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if notification.status not in [
            NotificationStatus.PENDING,
            NotificationStatus.QUEUED,
        ]:
            raise ValidationError({"detail": "This notification cannot be cancelled."})

        notification.status = NotificationStatus.CANCELLED
        notification.save(update_fields=["status", "updated_at"])

        return Response(
            {
                "detail": "Notification cancelled successfully.",
                "id": str(notification.id),
                "status": notification.status,
            },
            status=status.HTTP_200_OK,
        )
