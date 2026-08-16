from rest_framework import serializers

from accounts.serializers import DepartmentBriefSerializer
from courses.models import Course
from courses.serializers import CourseSerializer
from department.models import Department

from .models import Handout


class HandoutSerializer(serializers.ModelSerializer):
    course        = CourseSerializer(read_only=True)
    course_id     = serializers.PrimaryKeyRelatedField(
        queryset=Course.objects.all(),
        source="course",
        write_only=True,
    )
    department    = DepartmentBriefSerializer(read_only=True)
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.filter(is_active=True),
        source="department",
        write_only=True,
        required=False,
        allow_null=True,
    )
    in_stock      = serializers.SerializerMethodField()

    class Meta:
        model  = Handout
        fields = [
            "id", "title", "description", "price", "stock", "in_stock",
            "is_active", "course", "course_id", "department", "department_id",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than zero.")
        return value

    def get_in_stock(self, obj) -> bool:
        return obj.has_stock()
