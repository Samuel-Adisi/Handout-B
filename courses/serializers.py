from rest_framework import serializers
from .models import Course
from accounts.serializers import UserSerializer
from accounts.models import User

class CourseSerializer(serializers.ModelSerializer):
    rep           = UserSerializer(read_only=True)
    rep_id        = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role="rep"),
        source="rep",
        write_only=True,
        required=False  # ← not required, set in perform_create
    )
    handout_count = serializers.SerializerMethodField()

    class Meta:
        model  = Course
        fields = ["id", "name", "code", "description", "is_active", "rep", "rep_id", "handout_count", "created_at"]

    def get_handout_count(self, obj):
        return obj.handouts.filter(is_active=True).count()