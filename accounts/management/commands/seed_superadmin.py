from django.core.management.base import BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = 'Seed superadmin user'

    def handle(self, *args, **options):
        username = 'superadmin@pitpet.com'
        
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'Superadmin "{username}" sudah ada.'))
            return

        user = User(
            username=username,
            full_name='Super Admin',
            phone_number='081234567890',
            role='superadmin',
            password='superadmin123',
        )
        user.save()

        self.stdout.write(self.style.SUCCESS(
            f'Superadmin berhasil dibuat!\n'
            f'  Email    : {username}\n'
            f'  Password : superadmin123'
        ))
