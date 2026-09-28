from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from .models import Book, InventoryOperation, LibraryProfile, Loan, VirtualRequest

User = get_user_model()


class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class ProfileSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    role = serializers.CharField(read_only=True)

    class Meta:
        model = LibraryProfile
        fields = ["id", "user_id", "username", "first_name", "last_name", "email", "role", "national_id", "phone", "is_banned", "ban_reason"]
        read_only_fields = ["id", "is_banned", "ban_reason"]


class LoanSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="book.title", read_only=True)
    member_name = serializers.CharField(source="user.get_full_name", read_only=True)
    member_national_id = serializers.CharField(source="user.library_profile.national_id", read_only=True)
    member_phone = serializers.CharField(source="user.library_profile.phone", read_only=True)
    reviewed_by_name = serializers.CharField(source="reviewed_by.get_full_name", read_only=True)

    class Meta:
        model = Loan
        fields = ["id", "user", "book", "book_title", "member_name", "member_national_id", "member_phone", "status", "due_date", "created_at", "returned_at", "reviewed_by", "reviewed_by_name", "reviewed_at"]
        read_only_fields = ["id", "user", "status", "created_at", "returned_at", "due_date", "reviewed_by", "reviewed_at"]

    def validate(self, attrs):
        profile, _ = LibraryProfile.objects.get_or_create(user=self.context["request"].user)
        if not profile.national_id or not profile.phone:
            raise serializers.ValidationError("Completa tu CI y teléfono en tu perfil antes de alquilar.")
        return attrs


class VirtualRequestSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="book.title", read_only=True)
    member_name = serializers.CharField(source="user.get_full_name", read_only=True)
    member_national_id = serializers.CharField(source="user.library_profile.national_id", read_only=True)
    member_phone = serializers.CharField(source="user.library_profile.phone", read_only=True)
    reviewed_by_name = serializers.CharField(source="reviewed_by.get_full_name", read_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = VirtualRequest
        fields = ["id", "user", "book", "book_title", "member_name", "member_national_id", "member_phone", "status", "message", "created_at", "download_url", "reviewed_by", "reviewed_by_name"]
        read_only_fields = ["id", "user", "status", "created_at", "download_url", "reviewed_by"]

    def get_download_url(self, request):
        if request.status == VirtualRequest.Status.APPROVED:
            return request.book.virtual_url
        return ""


class InventoryOperationSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="book.title", read_only=True)
    performed_by_name = serializers.CharField(source="performed_by.get_full_name", read_only=True)

    class Meta:
        model = InventoryOperation
        fields = ["id", "book", "book_title", "performed_by", "performed_by_name", "kind", "quantity", "unit_price", "created_at"]
        read_only_fields = ["id", "performed_by", "created_at"]

    def create(self, validated_data):
        with transaction.atomic():
            book = Book.objects.select_for_update().get(pk=validated_data["book"].pk)
            quantity = validated_data["quantity"]
            if validated_data["kind"] == InventoryOperation.Kind.SALE and book.physical_stock < quantity:
                raise serializers.ValidationError({"quantity": "No hay suficientes ejemplares en inventario."})
            if validated_data["kind"] == InventoryOperation.Kind.PURCHASE:
                book.physical_stock += quantity
            else:
                book.physical_stock -= quantity
            book.save(update_fields=["physical_stock"])
            return InventoryOperation.objects.create(performed_by=self.context["request"].user, **validated_data)


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    national_id = serializers.CharField(max_length=24)
    phone = serializers.CharField(max_length=32)

    class Meta:
        model = User
        fields = ["username", "password", "first_name", "last_name", "email", "national_id", "phone"]

    def create(self, validated_data):
        national_id = validated_data.pop("national_id")
        phone = validated_data.pop("phone")
        user = User.objects.create_user(**validated_data)
        LibraryProfile.objects.create(user=user, national_id=national_id, phone=phone)
        return user