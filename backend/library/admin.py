from django.contrib import admin

from .models import Book, InventoryOperation, LibraryProfile, Loan, VirtualRequest


@admin.register(LibraryProfile)
class LibraryProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "national_id", "phone", "is_banned")
    list_filter = ("role", "is_banned")
    search_fields = ("user__username", "user__first_name", "user__last_name", "national_id")


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "physical_stock", "is_virtual")
    search_fields = ("title", "author")
    list_filter = ("is_virtual",)


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ("book", "user", "status", "due_date", "created_at")
    list_filter = ("status",)
    search_fields = ("book__title", "user__username", "user__library_profile__national_id")


@admin.register(VirtualRequest)
class VirtualRequestAdmin(admin.ModelAdmin):
    list_display = ("book", "user", "status", "created_at", "reviewed_by")
    list_filter = ("status",)


@admin.register(InventoryOperation)
class InventoryOperationAdmin(admin.ModelAdmin):
    list_display = ("book", "kind", "quantity", "unit_price", "performed_by", "created_at")
    list_filter = ("kind",)