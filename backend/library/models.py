from django.conf import settings
from django.db import models


class LibraryProfile(models.Model):
    class Role(models.TextChoices):
        ADMIN = "admin", "Administrador"
        LIBRARIAN = "librarian", "Bibliotecario"
        MEMBER = "member", "Usuario"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="library_profile")
    role = models.CharField(max_length=12, choices=Role.choices, default=Role.MEMBER)
    national_id = models.CharField("CI", max_length=24, unique=True, null=True, blank=True)
    phone = models.CharField("Teléfono", max_length=32, blank=True)
    is_banned = models.BooleanField(default=False)
    ban_reason = models.CharField(max_length=240, blank=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"


class Book(models.Model):
    title = models.CharField("Nombre", max_length=180)
    author = models.CharField("Autor", max_length=180)
    genres = models.JSONField(default=list, blank=True)
    cover_url = models.URLField("Foto de portada", blank=True)
    physical_stock = models.PositiveIntegerField(default=0)
    is_virtual = models.BooleanField(default=False)
    virtual_url = models.URLField(blank=True)
    purchase_price = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    sale_price = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    rental_price = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class Loan(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendiente"
        ACTIVE = "active", "Activo"
        RETURNED = "returned", "Devuelto"
        REJECTED = "rejected", "Rechazado"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="library_loans")
    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="loans")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    due_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_loans")
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class VirtualRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendiente"
        APPROVED = "approved", "Aprobada"
        REJECTED = "rejected", "Rechazada"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="virtual_requests")
    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="virtual_requests")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    message = models.CharField(max_length=500, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_virtual_requests")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class InventoryOperation(models.Model):
    class Kind(models.TextChoices):
        PURCHASE = "purchase", "Compra"
        SALE = "sale", "Venta"

    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="inventory_operations")
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    kind = models.CharField(max_length=12, choices=Kind.choices)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=9, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]