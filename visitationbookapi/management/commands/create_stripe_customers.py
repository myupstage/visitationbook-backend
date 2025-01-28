from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import stripe

User = get_user_model()

class Command(BaseCommand):
    help = 'Create Stripe customers for users without stripe_customer_id'

    def handle(self, *args, **kwargs):
        users = User.objects.filter(stripe_customer_id__isnull=True)
        for user in users:
            try:
                customer = stripe.Customer.create(
                    email=user.email,
                    name=user.full_name,
                    metadata={
                        'user_id': str(user.id)
                    }
                )
                user.stripe_customer_id = customer.id
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Created Stripe customer for {user.email}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error creating customer for {user.email}: {str(e)}"))