from rest_framework import serializers
from .models import Payment
from handouts.models import Handout
from handouts.serializers import HandoutSerializer
from accounts.serializers import UserSerializer
class PaymentSerializer(serializers.ModelSerializer):
    student      = UserSerializer(read_only=True)
    handout      = HandoutSerializer(read_only=True)
    handout_id   = serializers.PrimaryKeyRelatedField(
        queryset=Handout.objects.filter(is_active=True),
        source="handout",
        write_only=True
    )
    momo_number  = serializers.CharField()

    class Meta:
        model  = Payment
        fields = [
            "id", "student", "handout", "handout_id",
            "amount", "momo_number",
            "reference", "status", "created_at", "confirmed_at"
        ]
        read_only_fields = ["id", "amount", "reference", "status", "confirmed_at"]

    def validate(self, attrs):
        request = self.context.get("request")
        handout = attrs.get("handout")

        if not handout:
            raise serializers.ValidationError({"handout_id": "Handout is required."})

        if not handout.has_stock():
            raise serializers.ValidationError({"handout": "This handout is out of stock."})

        existing = Payment.objects.filter(
            student=request.user,
            handout=handout,
        ).first()

        if existing:
            if existing.status == "successful":
                raise serializers.ValidationError(
                    {"handout": "You have already paid for this handout."}
                )
            elif existing.status == "pending":
                raise serializers.ValidationError(
                    {"handout": "You have a pending payment. Check your phone for the MoMo prompt."}
                )
            elif existing.status in ["failed", "expired"]:
                existing.delete()

        # Replace:
        attrs["student"] = request.user
        attrs["amount"]  = handout.price
        return attrs

class PaymentStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Payment
        fields = ["id", "status", "reference", "confirmed_at"]