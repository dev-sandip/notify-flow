from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()
# Serializers in Django REST Framework are used to convert complex data types, such as Django models, into native Python datatypes that can then be easily rendered into JSON or other content types. They also handle validation and deserialization of input data. In this code snippet, several serializers are defined for user registration, user details, profile updates, logout, and password changes. Each serializer specifies the model it is associated with and the fields to be included, along with validation logic to ensure data integrity and security.


class RegisterSerializer(serializers.ModelSerializer):
    # Here passowrd and confirm_password are defined as write-only fields, meaning they will not be included in the serialized output. The password field also includes a validator to ensure that it meets the required password complexity standards. The confirm_password field is used to verify that the user has entered the same password twice during registration.
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
        style={"input_type": "password"},
    )
    confirm_password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )

    # Meta class in Django REST Framework serializers is used to specify additional options for the serializer, such as the model it is associated with and the fields to be included. In this code snippet, the Meta class defines the model as User and specifies the fields to be included in the serializer, along with read-only fields. It also includes validation methods for email uniqueness and password confirmation, as well as a create method to handle user creation with the provided validated data.
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "password",
            "confirm_password",
        ]
        read_only_fields = ["id"]

    # validate_email method is a custom validation method that checks if the provided email already exists in the database. If it does, a ValidationError is raised, indicating that an account with this email already exists. The validate method checks if the password and confirm_password fields match, raising a ValidationError if they do not. The create method is responsible for creating a new user instance using the validated data, ensuring that the password is set correctly and that the confirm_password field is not included in the final user creation process.
    def validate_email(self, value):
        value = value.strip().lower()

        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "An account with this email already exists."
            )

        return value

    # validate method is a custom validation method that checks if the provided password and confirm_password fields match. If they do not match, a ValidationError is raised, indicating that the passwords do not match. This ensures that users enter their desired password correctly during registration.
    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )

        return attrs

    # create method is responsible for creating a new user instance using the validated data. It removes the confirm_password field from the validated data, as it is not needed for user creation. The password is also extracted from the validated data and passed to the create_user method of the User model, which handles the actual creation of the user instance with the provided email and password.
    def create(self, validated_data):
        validated_data.pop("confirm_password")
        password = validated_data.pop("password")

        return User.objects.create_user(
            password=password,
            **validated_data,
        )


# UserSerializer is a serializer class that defines how user data should be serialized and deserialized. It specifies the model as User and includes fields such as id, email, first_name, last_name, and date_joined. The read_only_fields attribute indicates that the id, email, and date_joined fields should not be modified during serialization or deserialization. This serializer is typically used for retrieving user details in API responses.
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "date_joined",
        ]
        read_only_fields = ["id", "email", "date_joined"]


# ProfileUpdateSerializer is a serializer class that defines how user profile data should be serialized and deserialized. It specifies the model as User and includes fields such as first_name and last_name. This serializer is typically used for updating user profile information in API requests, allowing users to modify their first and last names while keeping other fields unchanged.
class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["first_name", "last_name"]


# LogoutSerializer is a serializer class that handles the logout functionality by validating and blacklisting refresh tokens. It defines a refresh field to accept the refresh token from the request. The validate method checks if the provided refresh token is valid and not expired, raising a ValidationError if it is invalid. The save method blacklists the refresh token, preventing it from being used again for authentication. If the token is already invalid, a ValidationError is raised to indicate that the token cannot be blacklisted again.
class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, attrs):
        try:
            self.token = RefreshToken(attrs["refresh"])
        except TokenError:
            raise serializers.ValidationError(
                {"refresh": "Invalid or expired refresh token."}
            )

        return attrs

    def save(self, **kwargs):
        try:
            self.token.blacklist()
        except TokenError:
            raise serializers.ValidationError(
                {"refresh": "This refresh token is already invalid."}
            )


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
    )
    confirm_new_password = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context["request"].user

        if not user.check_password(value):
            raise serializers.ValidationError("Incorrect current password.")

        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_new_password"]:
            raise serializers.ValidationError(
                {"confirm_new_password": "Passwords do not match."}
            )

        if attrs["old_password"] == attrs["new_password"]:
            raise serializers.ValidationError(
                {"new_password": "New password must be different."}
            )

        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])

        # Invalidate all outstanding refresh tokens for this user.
        from rest_framework_simplejwt.token_blacklist.models import (
            BlacklistedToken,
            OutstandingToken,
        )

        outstanding_tokens = OutstandingToken.objects.filter(user=user)

        for token in outstanding_tokens:
            BlacklistedToken.objects.get_or_create(token=token)

        return user
