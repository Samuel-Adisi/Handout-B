from rest_framework import serializers
from .models import Handout
from courses.serializers import CourseSerializer


class HandoutSerializer(serializers.ModelSerializer):
    course      = CourseSerializer(read_only=True)
    course_id   = serializers.PrimaryKeyRelatedField(
                    queryset=__import__("courses.models", fromlist=["Course"]).Course.objects.all(),
                    source="course",
                    write_only=True
                  )
    in_stock    = serializers.SerializerMethodField()

    class Meta:
        model  = Handout
        fields = ["id", "title", "description", "price", "stock", "in_stock", "is_active", "course", "course_id", "created_at"]




    def get_in_stock(self, obj):
        return obj.has_stock()