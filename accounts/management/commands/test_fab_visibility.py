from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Test FAB visibility logic for different user types'

    def handle(self, *args, **options):
        users = User.objects.all()
        
        self.stdout.write(self.style.SUCCESS('FAB Visibility Test'))
        self.stdout.write('=' * 50)
        
        for user in users:
            roles = user.get_roles_list()
            has_general = 'general' in roles
            show_fab = (user.is_authenticated and 
                       not user.is_staff and 
                       not user.is_superuser and 
                       has_general)
            
            status = "✓ SHOW FAB" if show_fab else "✗ HIDE FAB"
            
            self.stdout.write(f'{user.username:<15} | Roles: {str(roles):<25} | {status}')
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Summary:'))
        general_users = User.objects.filter(service_roles__icontains='general')
        eligible_users = [u for u in general_users if not u.is_staff and not u.is_superuser]
        
        self.stdout.write(f'Users eligible for FAB: {len(eligible_users)}')
        for user in eligible_users:
            self.stdout.write(f'  - {user.username}')