from datetime import timedelta

from django.contrib.auth import authenticate, get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import filters, mixins, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Book, InventoryOperation, LibraryProfile, Loan, VirtualRequest
from .permissions import IsAdmin, IsStaff, IsStaffOrReadOnly, is_staff_member, role_for
from .serializers import BookSerializer, InventoryOperationSerializer, LoanSerializer, ProfileSerializer, SignupSerializer, VirtualRequestSerializer

User = get_user_model()


def user_summary(user):
    profile, _ = LibraryProfile.objects.get_or_create(user=user)
    if user.is_superuser and profile.role != LibraryProfile.Role.ADMIN:
        profile.role = LibraryProfile.Role.ADMIN
        profile.save(update_fields=["role"])
    return {"id": user.id, "username": user.username, "first_name": user.first_name, "last_name": user.last_name, "role": role_for(user), "is_banned": profile.is_banned}


@api_view(["POST"])
@permission_classes([AllowAny])
def signup(request):
    serializer = SignupSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    token, _ = Token.objects.get_or_create(user=user)
    return Response({"token": token.key, "user": user_summary(user)}, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    user = authenticate(username=request.data.get("username"), password=request.data.get("password"))
    if not user:
        return Response({"detail": "Usuario o contraseña incorrectos."}, status=status.HTTP_400_BAD_REQUEST)
    token, _ = Token.objects.get_or_create(user=user)
    return Response({"token": token.key, "user": user_summary(user)})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    profile, _ = LibraryProfile.objects.get_or_create(user=request.user)
    if request.user.is_superuser and profile.role != LibraryProfile.Role.ADMIN:
        profile.role = LibraryProfile.Role.ADMIN
        profile.save(update_fields=["role"])
    return Response(ProfileSerializer(profile).data)


class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [IsStaffOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "author"]
    ordering_fields = ["title", "author", "created_at"]


class LoanViewSet(viewsets.ModelViewSet):
    serializer_class = LoanSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        loans = Loan.objects.select_related("book", "user")
        return loans if is_staff_member(self.request.user) else loans.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile, _ = LibraryProfile.objects.get_or_create(user=request.user)
        if profile.is_banned:
            return Response({"detail": "Tu cuenta está suspendida: " + profile.ban_reason}, status=status.HTTP_403_FORBIDDEN)
        with transaction.atomic():
            book = get_object_or_404(Book.objects.select_for_update(), pk=serializer.validated_data["book"].pk)
            if book.physical_stock < 1:
                return Response({"detail": "No hay ejemplares físicos disponibles."}, status=status.HTTP_400_BAD_REQUEST)
            loan = Loan.objects.create(user=request.user, book=book, due_date=timezone.localdate() + timedelta(days=14), status=Loan.Status.PENDING)
        return Response(self.get_serializer(loan).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        if not is_staff_member(request.user):
            return Response({"detail": "Solo el personal puede aprobar alquileres."}, status=status.HTTP_403_FORBIDDEN)
        with transaction.atomic():
            loan = get_object_or_404(Loan.objects.select_for_update(), pk=pk)
            if loan.status != Loan.Status.PENDING:
                return Response({"detail": "El alquiler ya fue revisado."}, status=status.HTTP_400_BAD_REQUEST)
            book = get_object_or_404(Book.objects.select_for_update(), pk=loan.book_id)
            if book.physical_stock < 1:
                return Response({"detail": "No hay ejemplares físicos disponibles."}, status=status.HTTP_400_BAD_REQUEST)
            book.physical_stock -= 1
            book.save(update_fields=["physical_stock"])
            loan.status = Loan.Status.ACTIVE
            loan.reviewed_by = request.user
            loan.reviewed_at = timezone.now()
            loan.save(update_fields=["status", "reviewed_by", "reviewed_at"])
        return Response(self.get_serializer(loan).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        if not is_staff_member(request.user):
            return Response({"detail": "Solo el personal puede rechazar alquileres."}, status=status.HTTP_403_FORBIDDEN)
        loan = self.get_object()
        if loan.status != Loan.Status.PENDING:
            return Response({"detail": "El alquiler ya fue revisado."}, status=status.HTTP_400_BAD_REQUEST)
        loan.status = Loan.Status.REJECTED
        loan.reviewed_by = request.user
        loan.reviewed_at = timezone.now()
        loan.save(update_fields=["status", "reviewed_by", "reviewed_at"])
        return Response(self.get_serializer(loan).data)

    @action(detail=True, methods=["post"], url_path="return")
    def return_book(self, request, pk=None):
        if not is_staff_member(request.user):
            return Response({"detail": "Solo el personal puede registrar devoluciones."}, status=status.HTTP_403_FORBIDDEN)
        with transaction.atomic():
            loan = get_object_or_404(Loan.objects.select_for_update().select_related("book"), pk=pk)
            if loan.status == Loan.Status.ACTIVE:
                loan.status = Loan.Status.RETURNED
                loan.returned_at = timezone.now()
                loan.save(update_fields=["status", "returned_at"])
                book = Book.objects.select_for_update().get(pk=loan.book_id)
                book.physical_stock += 1
                book.save(update_fields=["physical_stock"])
        return Response(self.get_serializer(loan).data)


class VirtualRequestViewSet(viewsets.ModelViewSet):
    serializer_class = VirtualRequestSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        requests = VirtualRequest.objects.select_related("book", "user")
        return requests if is_staff_member(self.request.user) else requests.filter(user=self.request.user)

    def perform_create(self, serializer):
        profile, _ = LibraryProfile.objects.get_or_create(user=self.request.user)
        if profile.is_banned:
            raise PermissionDenied("Tu cuenta está suspendida: " + profile.ban_reason)
        if not serializer.validated_data["book"].is_virtual:
            raise ValidationError({"book": "Este título no tiene edición virtual."})
        serializer.save(user=self.request.user)

    def partial_update(self, request, *args, **kwargs):
        if not is_staff_member(request.user):
            return Response({"detail": "Solo el personal puede revisar solicitudes."}, status=status.HTTP_403_FORBIDDEN)
        instance = self.get_object()
        new_status = request.data.get("status")
        if new_status not in {VirtualRequest.Status.APPROVED, VirtualRequest.Status.REJECTED}:
            return Response({"detail": "Estado de revisión no válido."}, status=status.HTTP_400_BAD_REQUEST)
        instance.status = new_status
        instance.reviewed_by = request.user
        instance.save(update_fields=["status", "reviewed_by"])
        return Response(self.get_serializer(instance).data)


class InventoryOperationViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = InventoryOperation.objects.select_related("book", "performed_by")
    serializer_class = InventoryOperationSerializer
    permission_classes = [IsStaff]


class MemberViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LibraryProfile.objects.select_related("user")
    serializer_class = ProfileSerializer
    permission_classes = [IsStaff]

    @action(detail=True, methods=["post"])
    def ban(self, request, pk=None):
        profile = self.get_object()
        if profile.role == LibraryProfile.Role.ADMIN:
            return Response({"detail": "No se puede suspender una cuenta administradora."}, status=status.HTTP_400_BAD_REQUEST)
        profile.is_banned = True
        profile.ban_reason = request.data.get("reason", "Incumplimiento del reglamento")[:240]
        profile.save(update_fields=["is_banned", "ban_reason"])
        return Response(self.get_serializer(profile).data)

    @action(detail=True, methods=["post"])
    def unban(self, request, pk=None):
        profile = self.get_object()
        profile.is_banned = False
        profile.ban_reason = ""
        profile.save(update_fields=["is_banned", "ban_reason"])
        return Response(self.get_serializer(profile).data)

    @action(detail=True, methods=["patch"], permission_classes=[IsAdmin])
    def set_role(self, request, pk=None):
        profile = self.get_object()
        role = request.data.get("role")
        if role not in LibraryProfile.Role.values:
            return Response({"detail": "Rol no válido."}, status=status.HTTP_400_BAD_REQUEST)
        profile.role = role
        profile.save(update_fields=["role"])
        return Response(self.get_serializer(profile).data)