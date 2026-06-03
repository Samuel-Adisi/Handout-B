from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from django.conf import settings
from django.db import IntegrityError




class RegisterSerializer(serializers.ModelSerializer):
    password   = serializers.CharField(write_only=True, validators=[validate_password])
    name       = serializers.CharField(required=True)
    phone      = serializers.CharField(required=True)
    student_id = serializers.CharField(required=True)

    class Meta:
        model  = User
        fields = ["id", "name", "student_id", "phone", "role", "password"]

    def validate_student_id(self, value):
        if User.objects.filter(student_id=value.strip()).exists():
            raise serializers.ValidationError(
                "An account with this Student ID already exists."
            )
        return value.strip()

    def validate_role(self, value):
        if value in ["rep", "admin"]:
            raise serializers.ValidationError(
                "You cannot register as a rep or admin. Contact your administrator."
            )
        return value



    def validate_phone(self, value):
        phone = value.strip().replace(" ", "")
        if not phone.startswith("0") or len(phone) != 10 or not phone.isdigit():
            raise serializers.ValidationError(
                "Enter a valid Ghana phone number e.g. 0241234567"
            )
        return phone

    def create(self, validated_data):
        password = validated_data.pop("password")
        user     = User(**validated_data)
        user.set_password(password)
        try:
            user.save()
        except IntegrityError:
            raise serializers.ValidationError(
                {"student_id": "An account with this Student ID already exists."}
            )
        return user






class RepRegisterSerializer(serializers.ModelSerializer):
    password    = serializers.CharField(
        write_only=True,
        required=True,
        min_length=8,
        validators=[validate_password]
    )
    name        = serializers.CharField(required=True)
    phone       = serializers.CharField(required=True)
    student_id  = serializers.CharField(required=True)
    invite_code = serializers.CharField(required=True, write_only=True)

    class Meta:
        model  = User
        fields = ["id", "name", "student_id", "phone", "password", "invite_code"]

    def validate_invite_code(self, value):
        if value != settings.REP_INVITE_CODE:
            raise serializers.ValidationError("Invalid invite code.")
        return value

    def validate_phone(self, value):
        phone = value.strip().replace(" ", "")
        if not phone.startswith("0") or len(phone) != 10 or not phone.isdigit():
            raise serializers.ValidationError("Enter a valid Ghana phone number e.g. 0241234567")
        return phone

    def create(self, validated_data):
        validated_data.pop("invite_code")
        password = validated_data.pop("password")
        user     = User(**validated_data, role="rep")
        user.set_password(password)
        user.save()
        return user



class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = ["id", "name", "student_id", "phone", "role", "created_at"]


class StudentTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = "student_id"

    def validate(self, attrs):
        data = super().validate(attrs)
        data["role"] = self.user.role
        data["name"] = self.user.name
        data["id"]   = self.user.id
        return data

class StudentTokenObtainPairView(TokenObtainPairView):
    serializer_class = StudentTokenObtainPairSerializer