import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library.models import LibraryProfile


class Command(BaseCommand):
    help = "Create or repair the initial Render administrator when bootstrap secrets are configured."

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "").strip()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")

        if not password:
            self.stdout.write("Initial admin bootstrap is disabled; no bootstrap credentials are set.")
            return
        if not username or not email:
            raise CommandError("Set DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL, and DJANGO_SUPERUSER_PASSWORD together.")

        user_model = get_user_model()
        lookup = {user_model.USERNAME_FIELD: username}
        with transaction.atomic():
            user = user_model.objects.select_for_update().filter(**lookup).first()
            if user and not user.is_superuser:
                raise CommandError(
                    "The configured bootstrap username already belongs to a non-superuser. "
                    "Choose a different DJANGO_SUPERUSER_USERNAME; existing reader accounts are never promoted automatically."
                )

            created = user is None
            if created:
                user = user_model(**lookup)
            user.email = email
            user.is_active = True
            user.is_staff = True
            user.is_superuser = True
            user.set_password(password)
            user.save()

            profile, _ = LibraryProfile.objects.get_or_create(user=user)
            profile.role = LibraryProfile.Role.ADMIN
            profile.is_banned = False
            profile.ban_reason = ""
            profile.save(update_fields=["role", "is_banned", "ban_reason"])

        result = "created" if created else "repaired"
        self.stdout.write(self.style.SUCCESS(f"Initial administrator {result}: {username}"))