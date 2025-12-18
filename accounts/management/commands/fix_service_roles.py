"""
Management command to fix service_roles field format
Ensures all users have service_roles as comma-separated string, not object
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Fix service_roles field format for all users'

    def handle(self, *args, **options):
        self.stdout.write('Fixing service_roles format for all users...')
        
        fixed_count = 0
        error_count = 0
        
        for user in User.objects.all():
            try:
                # Check if service_roles is properly formatted as string
                if user.service_roles is None:
                    user.service_roles = 'general'
                    user.save(update_fields=['service_roles'])
                    fixed_count += 1
                    self.stdout.write(f'Fixed user {user.username}: None -> "general"')
                
                elif not isinstance(user.service_roles, str):
                    # Convert any non-string service_roles to string
                    user.service_roles = str(user.service_roles) if user.service_roles else 'general'
                    user.save(update_fields=['service_roles'])
                    fixed_count += 1
                    self.stdout.write(f'Fixed user {user.username}: converted to string')
                
                # Validate that has_role method works
                elif not hasattr(user, 'get_roles_list') or not callable(getattr(user, 'get_roles_list')):
                    self.stdout.write(
                        self.style.ERROR(f'User {user.username} missing get_roles_list method')
                    )
                    error_count += 1
                
                else:
                    # Test the role checking to ensure it works
                    try:
                        roles = user.get_roles_list()
                        test_result = user.has_role('general')  # Test method
                        self.stdout.write(f'User {user.username}: {len(roles)} roles, has_role works: {test_result}')
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'User {user.username} role check failed: {e}')
                        )
                        error_count += 1
                        
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error processing user {user.username}: {e}')
                )
                error_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Completed! Fixed {fixed_count} users, {error_count} errors.'
            )
        )