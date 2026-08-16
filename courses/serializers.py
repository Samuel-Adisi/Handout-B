from rest_framework import serializers

from accounts.models import User
from accounts.serializers import UserSerializer

from .models import Course


class CourseSerializer(serializers.ModelSerializer):
    rep           = UserSerializer(read_only=True)
    rep_id        = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role="rep"),
        source="rep",
        write_only=True,
        required=False,  # set from request.user in perform_create for reps
    )
    handout_count = serializers.SerializerMethodField()

    class Meta:
        model  = Course
        fields = [
            "id", "name", "code", "description", "is_active",
            "rep", "rep_id", "handout_count", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_code(self, value):
        return value.strip().upper()

    def get_handout_count(self, obj) -> int:
        # Uses the annotation from CourseScopeMixin when present; the fallback
        # keeps the serializer usable outside those views.
        count = getattr(obj, "active_handout_count", None)
        if count is None:
            return obj.handouts.filter(is_active=True).count()
        return count
