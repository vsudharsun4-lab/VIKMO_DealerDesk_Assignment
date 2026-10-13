"""Serializers for Products and Dealers."""
from decimal import Decimal, InvalidOperation

from rest_framework import serializers

from .models import Dealer, Product


# ── Helpers ───────────────────────────────────────────────────────────────────

def _validate_price(value):
    """Price must be > 0 and have at most 2 decimal places."""
    try:
        d = Decimal(str(value))
    except InvalidOperation:
        raise serializers.ValidationError("Price must be a valid decimal.")
    if d <= 0:
        raise serializers.ValidationError("Price must be greater than 0.")
    if d.as_tuple().exponent < -2:
        raise serializers.ValidationError("Price must have at most 2 decimal places.")
    return d


# ── Product ───────────────────────────────────────────────────────────────────

class ProductSerializer(serializers.ModelSerializer):
    price = serializers.SerializerMethodField()
    stock = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "sku", "name", "category", "brand",
            "vehicle_fitment", "price", "stock", "description",
        ]
        read_only_fields = ["sku", "stock"]

    def get_price(self, obj):
        return f"{obj.price:.2f}"


class ProductCreateSerializer(serializers.Serializer):
    sku = serializers.CharField(max_length=50)
    name = serializers.CharField(max_length=255)
    category = serializers.CharField(max_length=100)
    brand = serializers.CharField(max_length=100)
    vehicle_fitment = serializers.CharField(max_length=255)
    price = serializers.CharField()
    description = serializers.CharField(default="", allow_blank=True)

    def validate_price(self, value):
        return _validate_price(value)

    def create(self, validated_data):
        return Product.objects.create(**validated_data, stock=0)


class ProductPatchSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    category = serializers.CharField(max_length=100, required=False)
    brand = serializers.CharField(max_length=100, required=False)
    vehicle_fitment = serializers.CharField(max_length=255, required=False)
    price = serializers.CharField(required=False)
    description = serializers.CharField(required=False, allow_blank=True)

    def validate_price(self, value):
        return _validate_price(value)

    def update(self, instance, validated_data):
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        return instance


# ── Dealer ────────────────────────────────────────────────────────────────────

class DealerSerializer(serializers.ModelSerializer):
    credit_limit = serializers.SerializerMethodField()

    class Meta:
        model = Dealer
        fields = [
            "id", "dealer_code", "name", "city",
            "phone", "email", "gstin", "credit_limit",
        ]

    def get_credit_limit(self, obj):
        return f"{obj.credit_limit:.2f}"


class DealerCreateSerializer(serializers.Serializer):
    dealer_code = serializers.CharField(max_length=50)
    name = serializers.CharField(max_length=255)
    city = serializers.CharField(max_length=100, default="", allow_blank=True)
    phone = serializers.CharField(max_length=50, default="", allow_blank=True)
    email = serializers.EmailField(default="", allow_blank=True)
    gstin = serializers.CharField(max_length=20, default="", allow_blank=True)
    credit_limit = serializers.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"), required=False)

    def create(self, validated_data):
        return Dealer.objects.create(**validated_data)
