from django.db import transaction
from rest_framework import serializers

from accounts.serializers import UserSerializer
from accounts.validators import normalise_gh_phone
from handouts.models import Handout
from handouts.serializers import HandoutSerializer

from .models import Payment
from .services import available_stock


class PaymentSerializer(serializers.ModelSerializer):
    student       = UserSerializer(read_only=True)
    handout       = HandoutSerializer(read_only=True)
    handout_id    = serializers.PrimaryKeyRelatedField(
        queryset=Handout.objects.filter(is_active=True),
        source="handout",
        write_only=True,
    )
    momo_number   = serializers.CharField()
    momo_provider = serializers.ChoiceField(
        choices=Payment.PROVIDER_CHOICES, default="mtn"
    )

    class Meta:
        model  = Payment
        fields = [
            "id", "student", "handout", "handout_id",
            "amount", "momo_number", "momo_provider",
            "reference", "status", "created_at", "confirmed_at",
        ]
        # amount is derived from the handout: a client must never be able to
        # name its own price.
        read_only_fields = ["id", "amount", "reference", "status", "confirmed_at", "created_at"]

    def validate_momo_number(self, value):
        return normalise_gh_phone(value)

    def validate(self, attrs):
        request = self.context["request"]
        handout = attrs["handout"]
        student = request.user

        if student.department_id and handout.department_id and (
            handout.department_id != student.department_id
        ):
            raise serializers.ValidationError(
                {"handout_id": "This handout is not offered by your department."}
            )

        if Payment.objects.filter(
            student=student, handout=handout, status="successful"
        ).exists():
            raise serializers.ValidationError(
                {"handout": "You have already paid for this handout."}
            )

        if Payment.objects.filter(
            student=student, handout=handout, status__in=Payment.OPEN_STATUSES
        ).exists():
            raise serializers.ValidationError(
                {"handout": "You have a pending payment. Check your phone for the MoMo prompt."}
            )

        attrs["student"] = student
        attrs["amount"]  = handout.price
        return attrs

    def create(self, validated_data):
        handout = validated_data["handout"]

        # Lock the handout so concurrent buyers are serialised, then re-check
        # availability inside the lock. Previously the stock test lived in
        # validate() with nothing to stop N students passing it at once.
        with transaction.atomic():
            locked = Handout.objects.select_for_update().get(pk=handout.pk)
            if available_stock(locked) <= 0:
                raise serializers.ValidationError(
                    {"handout": "This handout is out of stock."}
                )
            return Payment.objects.create(**validated_data)


class PaymentStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Payment
        fields = ["id", "status", "reference", "confirmed_at"]
        read_only_fields = fields
