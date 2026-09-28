from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Book, LibraryProfile, Loan

User = get_user_model()


class LibraryWorkflowTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user(username="reader", password="reader-pass-123")
        LibraryProfile.objects.create(user=self.member, national_id="CI-101", phone="70000001")
        self.librarian = User.objects.create_user(username="staff", password="staff-pass-123")
        LibraryProfile.objects.create(user=self.librarian, role=LibraryProfile.Role.LIBRARIAN)
        self.book = Book.objects.create(title="Libro de prueba", author="Autora", physical_stock=1, is_virtual=True, virtual_url="https://example.com/ebook")
        self.member_client = APIClient()
        self.member_client.force_authenticate(self.member)
        self.librarian_client = APIClient()
        self.librarian_client.force_authenticate(self.librarian)

    def test_rental_waits_for_librarian_approval_before_stock_decreases(self):
        response = self.member_client.post("/api/loans/", {"book": self.book.id}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], Loan.Status.PENDING)
        self.book.refresh_from_db()
        self.assertEqual(self.book.physical_stock, 1)

        approval = self.librarian_client.post(f"/api/loans/{response.data['id']}/approve/")
        self.assertEqual(approval.status_code, 200)
        self.assertEqual(approval.data["status"], Loan.Status.ACTIVE)
        self.book.refresh_from_db()
        self.assertEqual(self.book.physical_stock, 0)

    def test_member_cannot_approve_rental(self):
        loan = Loan.objects.create(user=self.member, book=self.book, due_date=date.today(), status=Loan.Status.PENDING)
        response = self.member_client.post(f"/api/loans/{loan.id}/approve/")
        self.assertEqual(response.status_code, 403)

    def test_librarian_can_create_update_and_delete_books(self):
        created = self.librarian_client.post("/api/books/", {"title": "Nuevo", "author": "Autor", "physical_stock": 2}, format="json")
        self.assertEqual(created.status_code, 201)
        book_id = created.data["id"]
        updated = self.librarian_client.patch(f"/api/books/{book_id}/", {"title": "Actualizado"}, format="json")
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data["title"], "Actualizado")
        deleted = self.librarian_client.delete(f"/api/books/{book_id}/")
        self.assertEqual(deleted.status_code, 204)

    def test_member_cannot_modify_catalog(self):
        response = self.member_client.post("/api/books/", {"title": "No autorizado", "author": "Autor"}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_virtual_download_is_released_after_librarian_approval(self):
        requested = self.member_client.post("/api/virtual-requests/", {"book": self.book.id}, format="json")
        self.assertEqual(requested.status_code, 201)
        self.assertEqual(requested.data["download_url"], "")
        approved = self.librarian_client.patch(f"/api/virtual-requests/{requested.data['id']}/", {"status": "approved"}, format="json")
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.data["download_url"], self.book.virtual_url)
