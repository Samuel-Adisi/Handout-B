from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.db import IntegrityError
from django.utils.crypto import constant_time_compare
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from department.models import Department

from .models import User
from .validators import normalise_gh_phone


class DepartmentBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Department
        fields = ["id", "name", "department_type"]


class RegisterSerializer(serializers.ModelSerializer):
    password      = serializers.CharField(write_only=True, validators=[validate_password])
    name          = serializers.CharField(required=True)
    phone         = serializers.CharField(required=True)
    student_id    = serializers.CharField(required=True)
    department    = DepartmentBriefSerializer(read_only=True)
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.filter(is_active=True),
        source="department",
        write_only=True,
    )

    class Meta:
        model  = User
        fields = ["id", "name", "student_id", "phone", "role", "department", "department_id", "password"]
        # `role` is output only: it must never be settable from a public,
        # unauthenticated signup body.
        read_only_fields = ["id", "role"]

    def validate_student_id(self, value):
        student_id = value.strip()
        if User.objects.filter(student_id__iexact=student_id).exists():
            raise serializers.ValidationError(
                "An account with this Student ID already exists."
            )
        return student_id

    def validate_phone(self, value):
        return normalise_gh_phone(value)

    def create(self, validated_data):
        password = validated_data.pop("password")
        user     = User(**validated_data, role="student")
        user.set_password(password)
        try:
            user.save()
        except IntegrityError:
            # Lost the race against a concurrent signup with the same ID.
            raise serializers.ValidationError(
                {"student_id": "An account with this Student ID already exists."}
            )
        return user


class RepRegisterSerializer(serializers.ModelSerializer):
    password      = serializers.CharField(
        write_only=True,
        required=True,
        min_length=8,
        validators=[validate_password],
    )
    name          = serializers.CharField(required=True)
    phone         = serializers.CharField(required=True)
    student_id    = serializers.CharField(required=True)
    invite_code   = serializers.CharField(required=True, write_only=True)
    department    = DepartmentBriefSerializer(read_only=True)
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.filter(is_active=True),
        source="department",
        write_only=True,
    )

    class Meta:
        model  = User
        fields = [
            "id", "name", "student_id", "phone", "password",
            "department", "department_id", "invite_code",
        ]
        read_only_fields = ["id"]

    def validate_invite_code(self, value):
        expected = settings.REP_INVITE_CODE
        # Fail closed: with no code configured, nobody may self-register as rep.
        if not expected:
            raise serializers.ValidationError(
                "Course rep registration is not available. Contact your administrator."
            )
        # Constant time so the code cannot be recovered a character at a time.
        if not constant_time_compare(value, expected):
            raise serializers.ValidationError("Invalid invite code.")
        return value

    def validate_student_id(self, value):
        student_id = value.strip()
        if User.objects.filter(student_id__iexact=student_id).exists():
            raise serializers.ValidationError(
                "An account with this Student ID already exists."
            )
        return student_id

    def validate_phone(self, value):
        return normalise_gh_phone(value)

    def create(self, validated_data):
        validated_data.pop("invite_code")
        password = validated_data.pop("password")
        user     = User(**validated_data, role="rep")
        user.set_password(password)
        try:
            user.save()
        except IntegrityError:
            raise serializers.ValidationError(
                {"student_id": "An account with this Student ID already exists."}
            )
        return user


class UserSerializer(serializers.ModelSerializer):
    """Profile representation used by /me/ and nested in other payloads.

    `role` and `student_id` are read-only: /me/ accepts PATCH, and a writable
    `role` let any student promote themselves to admin.
    """

    department    = DepartmentBriefSerializer(read_only=True)
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.filter(is_active=True),
        source="department",
        write_only=True,
        required=False,
    )

    class Meta:
        model  = User
        fields = [
            "id", "name", "student_id", "phone", "role",
            "department", "department_id", "created_at",
        ]
        read_only_fields = ["id", "student_id", "role", "created_at"]

    def validate_phone(self, value):
        return normalise_gh_phone(value)


class StudentTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = "student_id"

    def validate(self, attrs):
        data = super().validate(attrs)
        data["role"] = self.user.role
        data["name"] = self.user.name
        data["id"]   = self.user.id
        return data
