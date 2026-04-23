from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create admin user for SmartInv"

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True, help="Admin username")
        parser.add_argument("--password", required=True, help="Admin password")
        parser.add_argument("--email", default="", help="Admin email")

    def handle(self, *args, **options):
        user_model = get_user_model()
        username = options["username"].strip()
        password = options["password"]
        email = options["email"].strip()

        if user_model.objects.filter(username=username).exists():
            raise CommandError(f"User '{username}' already exists")

        user_model.objects.create_superuser(username=username, password=password, email=email)
        self.stdout.write(self.style.SUCCESS(f"Admin '{username}' created successfully."))
