from django.core.management.base import BaseCommand
from hospital.models import CustomUser


class Command(BaseCommand):
    help = 'Creates an admin user with username SwasthyaCare and password CodeClashers@'

    def handle(self, *args, **kwargs):
        username = 'SwasthyaCare'
        password = 'CodeClashers@'
        
        # Check if admin user already exists
        if CustomUser.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'Admin user "{username}" already exists.'))
            return
        
        # Create admin user
        admin_user = CustomUser.objects.create_user(
            username=username,
            password=password,
            first_name='Admin',
            last_name='SwasthyaCare',
            email='admin@swasthyacare.com',
            role='ADMIN'
        )
        
        self.stdout.write(self.style.SUCCESS(f'Successfully created admin user: {username}'))
        self.stdout.write(self.style.SUCCESS(f'Password: {password}'))
