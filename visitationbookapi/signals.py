from django.db.models.signals import post_save, pre_save
from django.core.mail import EmailMultiAlternatives
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.urls import reverse
from django_rest_passwordreset.signals import reset_password_token_created
from visitationbook import settings
from django.db import transaction
from visitationbookapi.models import *
import stripe
from django.contrib.staticfiles.storage import staticfiles_storage


@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, *args, **kwargs):
    """
    Handles password reset tokens
    When a token is created, an e-mail needs to be sent to the user
    :param sender: View Class that sent the signal
    :param instance: View Instance that sent the signal
    :param reset_password_token: Token Model Object
    :param args:
    :param kwargs:
    :return:
    """
    
    logo_url = f'{settings.BASE_URL}{staticfiles_storage.url("images/logo.png")}'
    
    # send an e-mail to the user
    otp_code = reset_password_token.key
    context = {
        'current_user': reset_password_token.user,
        'full_name': reset_password_token.user.full_name,
        'email': reset_password_token.user.email,
        'otp_code': otp_code,
        'reset_password_url': "{}?token={}".format(
            instance.request.build_absolute_uri(reverse('password_reset:reset-password-confirm')), 
            otp_code
        ),
        'logo_url': logo_url
    }

    email_html_message = render_to_string('email/user_reset_password.html', context)
    email_plaintext_message = render_to_string('email/user_reset_password.txt', context)

    msg = EmailMultiAlternatives(
        "Password Reset for Visitation Book",
        email_plaintext_message,
        settings.DEFAULT_FROM_EMAIL,
        [reset_password_token.user.email]
    )
    msg.attach_alternative(email_html_message, "text/html")
    msg.send()


@receiver(post_save, sender=GuestInfo)
def update_pdf_on_guest_info_change(sender, instance, created, **kwargs):
    # Mettre à jour le PDF chaque fois qu'un GuestInfo est créé ou modifié
    update_pdf(instance.book_purchase)
    
            
def create_stripe_customer(user):
    try:
        stripe_customer = stripe.Customer.create(
            email=user.email,
            name=user.full_name
        )

        user.stripe_customer_id = stripe_customer.id
        user.save()

        return stripe_customer.id
    except stripe.error.StripeError as e:
        print(f"Stripe error during customer creation : {str(e)}")
        return None


@transaction.atomic
def user_post_save(sender, instance, created, **kwargs):
    if created:
        stripe_customer_id = create_stripe_customer(instance)
        if stripe_customer_id:
            print(f"Stripe client successfully created for {instance.email}")
        else:
            print(f"Stripe client creation fails for {instance.email}")


post_save.connect(user_post_save, sender=User)
