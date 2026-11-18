import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import UserManager


# UserManager is a custom user manager that extends Django's BaseUserManager. It provides methods for creating regular users and superusers, ensuring that the email field is required and normalized. The User model itself extends AbstractUser, replacing the username field with an email field as the unique identifier for authentication.
# AbstractUser is a built-in Django model that provides the basic fields and methods for user authentication. By extending AbstractUser, the User model inherits these features while allowing customization, such as using email instead of username for authentication.
class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None
    email = models.EmailField(unique=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UserManager()

    def __str__(self):
        return self.email
