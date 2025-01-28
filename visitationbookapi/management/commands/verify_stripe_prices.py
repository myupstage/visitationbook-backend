from django.core.management.base import BaseCommand
from visitationbookapi.models import SubscriptionPlan
import stripe

class Command(BaseCommand):
    help = 'Verify and update Stripe price IDs for subscription plans'

    def handle(self, *args, **kwargs):
        plans = SubscriptionPlan.objects.all()
        for plan in plans:
            if not plan.stripe_price_id:
                try:
                    # Créer le prix dans Stripe
                    stripe_price = stripe.Price.create(
                        unit_amount=int(plan.price * 100),
                        currency='usd',  # ou 'eur'
                        recurring={
                            'interval': 'month',
                            'interval_count': plan.duration_months
                        },
                        product_data={
                            'name': plan.name,
                            'metadata': {
                                'plan_id': str(plan.id),
                                'plan_type': plan.plan_type,
                                'book_type': plan.book_type
                            }
                        }
                    )
                    plan.stripe_price_id = stripe_price.id
                    plan.save()
                    self.stdout.write(self.style.SUCCESS(f"Created price for plan {plan.name}: {stripe_price.id}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error creating price for plan {plan.name}: {str(e)}"))