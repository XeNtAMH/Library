from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Book",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=180, verbose_name="Nombre")),
                ("author", models.CharField(max_length=180, verbose_name="Autor")),
                ("genres", models.JSONField(blank=True, default=list)),
                ("cover_url", models.URLField(blank=True, verbose_name="Foto de portada")),
                ("physical_stock", models.PositiveIntegerField(default=0)),
                ("is_virtual", models.BooleanField(default=False)),
                ("virtual_url", models.URLField(blank=True)),
                ("purchase_price", models.DecimalField(decimal_places=2, default=0, max_digits=9)),
                ("sale_price", models.DecimalField(decimal_places=2, default=0, max_digits=9)),
                ("rental_price", models.DecimalField(decimal_places=2, default=0, max_digits=9)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["title"]},
        ),
        migrations.CreateModel(
            name="LibraryProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("admin", "Administrador"), ("librarian", "Bibliotecario"), ("member", "Usuario")], default="member", max_length=12)),
                ("national_id", models.CharField(blank=True, max_length=24, null=True, unique=True, verbose_name="CI")),
                ("phone", models.CharField(blank=True, max_length=32, verbose_name="Teléfono")),
                ("is_banned", models.BooleanField(default=False)),
                ("ban_reason", models.CharField(blank=True, max_length=240)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="library_profile", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="InventoryOperation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("purchase", "Compra"), ("sale", "Venta")], max_length=12)),
                ("quantity", models.PositiveIntegerField()),
                ("unit_price", models.DecimalField(decimal_places=2, max_digits=9)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("book", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="inventory_operations", to="library.book")),
                ("performed_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="Loan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("active", "Activo"), ("returned", "Devuelto")], default="active", max_length=12)),
                ("due_date", models.DateField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("returned_at", models.DateTimeField(blank=True, null=True)),
                ("book", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="loans", to="library.book")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="library_loans", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="VirtualRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("pending", "Pendiente"), ("approved", "Aprobada"), ("rejected", "Rechazada")], default="pending", max_length=12)),
                ("message", models.CharField(blank=True, max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("book", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="virtual_requests", to="library.book")),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reviewed_virtual_requests", to=settings.AUTH_USER_MODEL)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="virtual_requests", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]