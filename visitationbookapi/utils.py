import os
import re
from io import BytesIO
from functools import wraps
from visitationbook import settings
from visitationbookapi.models import *
from rest_framework.views import exception_handler
from rest_framework.response import Response
from django.core.files.base import ContentFile
from django.core.mail import EmailMultiAlternatives
from django.contrib.staticfiles.storage import staticfiles_storage
from django.db.models import QuerySet
from django.template.loader import render_to_string
import tempfile
from weasyprint import HTML


def generate_pdf(book_purchase):
    """Génère le PDF principal du book purchase avec WeasyPrint."""
    try:
        # Vérifier les fichiers nécessaires
        if book_purchase.deceased_image and not os.path.exists(book_purchase.deceased_image.path):
            raise FileNotFoundError(f"Deceased image file not found: {book_purchase.deceased_image.path}")

        # Préparer les chemins des images
        background_image = book_purchase.custom_cover.path if book_purchase.custom_cover else book_purchase.book.cover.path
        deceased_image = book_purchase.deceased_image.path if book_purchase.deceased_image else None
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.png')

        with tempfile.TemporaryDirectory() as tmpdirname:
            # Copier les images dans le répertoire temporaire
            import shutil
            tmp_bg = os.path.join(tmpdirname, 'background.jpg')
            tmp_deceased = os.path.join(tmpdirname, 'deceased.jpg') if deceased_image else None
            tmp_logo = os.path.join(tmpdirname, 'logo.png')
            
            shutil.copy2(background_image, tmp_bg)
            if deceased_image:
                shutil.copy2(deceased_image, tmp_deceased)
            if os.path.exists(logo_path):
                shutil.copy2(logo_path, tmp_logo)

            # Préparer les données des visiteurs
            guest_cards = []
            for guest in book_purchase.guest_infos.all():
                guest_data = {
                    'name': guest.guest_name if book_purchase.allow_name else None,
                    'address': guest.guest_address if book_purchase.allow_address else None,
                    'email': guest.guest_email if book_purchase.allow_email else None,
                    'notes': guest.special_notes if book_purchase.allow_special_notes else None
                }

                if book_purchase.allow_picture and guest.guest_picture:
                    guest_image_path = os.path.join(tmpdirname, f'guest_{guest.id}.jpg')
                    shutil.copy2(guest.guest_picture.path, guest_image_path)
                    guest_data['image'] = guest_image_path

                guest_cards.append(guest_data)
                
            # Préparer les pages de visiteurs (4 visiteurs par page)
            visitor_pages = []
            cards_per_page = 4
            for i in range(0, len(guest_cards), cards_per_page):
                visitor_pages.append(guest_cards[i:i + cards_per_page])

            # Contexte pour le template
            context = {
                'deceased_name': book_purchase.deceased_name,
                'deceased_image': tmp_deceased,
                'date_of_birth': book_purchase.date_of_birth.strftime('%B %d, %Y') if book_purchase.date_of_birth else None,
                'date_of_death': book_purchase.date_of_death.strftime('%B %d, %Y') if book_purchase.date_of_death else None,
                'background_image': tmp_bg,
                'logo': tmp_logo,
                'visitor_pages': visitor_pages  # Pages déjà préparées
            }

            # Générer le HTML
            html_string = render_to_string('pdf/visitation_book.html', context)
            html_path = os.path.join(tmpdirname, 'output.html')
            
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_string)

            try:
                # Générer le PDF
                pdf_buffer = BytesIO()
                HTML(filename=html_path, base_url=tmpdirname).write_pdf(
                    pdf_buffer,
                    presentational_hints=True,
                    optimize_size=('fonts', 'images')
                )

                pdf = pdf_buffer.getvalue()
            finally:
                if os.path.exists(html_path):
                    os.unlink(html_path)
                pdf_buffer.close()
                
            return pdf

    except Exception as e:
        print(f"Error generating PDF: {e}")
        raise


def update_pdf(book_purchase):
    book_purchase.delete_existing_pdf()
    pdf = generate_pdf(book_purchase)
    book_purchase.pdf_file.save(f'book_purchase_{book_purchase.id}.pdf', ContentFile(pdf), save=True)
    

def send_welcome_email(user):
    logo_url = f'{settings.BASE_URL}{staticfiles_storage.url("images/logo.png")}'
    
    subject = "Welcome to Visitation Book"
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = user.email

    # Contexte pour le template
    context = {
        'full_name': user.full_name,
        'login_url': settings.FRONT_URL,
        'logo_url': logo_url
    }

    # Render email templates
    email_html_message = render_to_string('email/welcome_email.html', context)
    email_plaintext_message = render_to_string('email/welcome_email.txt', context)

    try:
        msg = EmailMultiAlternatives(
            subject,
            email_plaintext_message,
            from_email,
            [to_email]
        )
        msg.attach_alternative(email_html_message, "text/html")
        msg.send()
    except Exception as e:
        print(e)
        

def send_payment_confirmation_email(user, book_purchase):
    """
    Send a payment confirmation email to the customer.

    """
    logo_url = f'{settings.BASE_URL}{staticfiles_storage.url("images/logo.png")}'
    
    subject = "Payment Confirmation"
    recipient_email = user.email
    from_email = settings.DEFAULT_FROM_EMAIL

    book_cover_relative_url = book_purchase.custom_cover.url if book_purchase.custom_cover else book_purchase.book.cover.url
    book_cover_url = f'{settings.BASE_URL}{book_cover_relative_url}'

    context = {
        'user': user,
        'book_cover_url': book_cover_url,
        'purchase_date': book_purchase.created_at,
        'transaction_id': book_purchase.payment_transaction.id,
        'amount': book_purchase.book.price,
        'book_title': book_purchase.book.title,
        'payment_status': "Completed",
        'logo_url': logo_url,
    }

    email_html_message = render_to_string('email/payment_confirmation.html', context)
    email_plaintext_message = render_to_string('email/payment_confirmation.txt', context)

    try:
        email_message = EmailMultiAlternatives(
            subject,
            email_plaintext_message,
            from_email,
            [recipient_email]
        )
        email_message.attach_alternative(email_html_message, "text/html")
        email_message.send()
    except Exception as e:
        print(e)
        
        
def send_subscription_confirmation_email(user, subscription):
    """
    Send a subscription confirmation email to the customer.
    """
    logo_url = f'{settings.BASE_URL}{staticfiles_storage.url("images/logo.png")}'
    
    subject = "Subscription Confirmation"
    recipient_email = user.email
    from_email = settings.DEFAULT_FROM_EMAIL

    context = {
        'user': user,
        'subscription_plan': subscription.plan.name,
        'plan_type': subscription.plan.get_plan_type_display(),
        'book_type': subscription.plan.get_book_type_display(),
        'start_date': subscription.start_date,
        'end_date': subscription.end_date,
        'transaction_id': subscription.payment_transaction.id if subscription.payment_transaction else None,
        'amount': subscription.plan.price,
        'max_books': subscription.plan.max_books,
        'payment_status': "Completed",
        'logo_url': logo_url,
    }

    email_html_message = render_to_string('email/subscription_confirmation.html', context)
    email_plaintext_message = render_to_string('email/subscription_confirmation.txt', context)

    try:
        email_message = EmailMultiAlternatives(
            subject,
            email_plaintext_message,
            from_email,
            [recipient_email]
        )
        email_message.attach_alternative(email_html_message, "text/html")
        email_message.send()
    except Exception as e:
        print(e)


def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # Now add the HTTP status code to the response.
    if response is not None:
        response.data['status_code'] = response.status_code

    return response


def paginate(func):

    @wraps(func)
    def inner(self, *args, **kwargs):
        queryset = func(self, *args, **kwargs)
        assert isinstance(queryset, (list, QuerySet)), "apply_pagination expects a List or a QuerySet"

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    return inner


def get_full_url(path):
    if not path:
        return None
    return f"{settings.BASE_URL}{path}"


def social_user_handler(strategy, details, backend, user=None, *args, **kwargs):
    if user:
        # L'utilisateur existe déjà, mettons à jour ses informations
        changed = False
        if not user.full_name and details.get('fullname'):
            user.full_name = details['fullname']
            changed = True
        if not user.email and details.get('email'):
            user.email = details['email']
            changed = True

        # Mise à jour des IDs sociaux
        if backend.name == 'google-oauth2' and not user.google_id:
            user.google_id = kwargs.get('response', {}).get('sub')
            changed = True
        elif backend.name == 'facebook' and not user.facebook_id:
            user.facebook_id = kwargs.get('response', {}).get('id')
            changed = True

        # Mise à jour de l'avatar si disponible
        if kwargs.get('response', {}).get('picture') and not user.social_avatar:
            user.social_avatar = kwargs['response']['picture']
            changed = True

        if changed:
            user.save()
    else:
        # Création d'un nouvel utilisateur
        user = User.objects.create_user(
            email=details.get('email'),
            full_name=details.get('fullname'),
            username=details.get('email'),  # Utilisez l'email comme nom d'utilisateur
        )
        if backend.name == 'google-oauth2':
            user.google_id = kwargs.get('response', {}).get('sub')
        elif backend.name == 'facebook':
            user.facebook_id = kwargs.get('response', {}).get('id')
        
        if kwargs.get('response', {}).get('picture'):
            user.social_avatar = kwargs['response']['picture']
        
        user.save()

    return {'is_new': user is None, 'user': user}


def generate_thank_you_note_pdf(book_purchase, guest_info=None):
    """
    Génère un PDF de note de remerciement, soit comme template soit personnalisé pour un guest
    
    Args:
        book_purchase: L'instance BookPurchase
        guest_info: Optionnel. Si fourni, génère un PDF personnalisé pour ce guest
    """
    try:
        if book_purchase.deceased_image:
            if not os.path.exists(book_purchase.deceased_image.path):
                raise FileNotFoundError(f"Deceased image file not found: {book_purchase.deceased_image.path}")
        
        # Préparer le texte de la note
        if guest_info:
            context = {
                'guest_name': guest_info.guest_name or 'Guest',
                'guest_address': guest_info.guest_address or '',
                'guest_email': guest_info.guest_email or '',
                'deceased_name': book_purchase.deceased_name or '',
                'book_purchaser_name': book_purchase.user.full_name or book_purchase.user.email,
            }
            attending_note = substitute_variables(book_purchase.attending_note, context)
        else:
            attending_note = book_purchase.attending_note

        # Construire les URLs absolus pour les images
        background_image = book_purchase.custom_cover.path if book_purchase.custom_cover else book_purchase.book.cover.path
        deceased_image = book_purchase.deceased_image.path if book_purchase.deceased_image else None
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.png')

        # Contexte pour le template HTML
        template_context = {
            'deceased_name': book_purchase.deceased_name,
            'date_of_birth': book_purchase.date_of_birth.strftime('%B %d, %Y') if book_purchase.date_of_birth else None,
            'date_of_death': book_purchase.date_of_death.strftime('%B %d, %Y') if book_purchase.date_of_death else None,
            'attending_note': attending_note,
            'book_purchaser_name': book_purchase.user.full_name or book_purchase.user.email,
        }

        # Créer un dossier temporaire pour les assets
        with tempfile.TemporaryDirectory() as tmpdirname:
            # Copier les images dans le dossier temporaire
            tmp_bg = os.path.join(tmpdirname, 'background.jpg')
            tmp_deceased = os.path.join(tmpdirname, 'deceased.jpg') if deceased_image else None
            tmp_logo = os.path.join(tmpdirname, 'logo.png')
            
            import shutil
            shutil.copy2(background_image, tmp_bg)
            if deceased_image:
                shutil.copy2(deceased_image, tmp_deceased)
            if os.path.exists(logo_path):
                shutil.copy2(logo_path, tmp_logo)
            
            # Ajouter les chemins d'images au contexte
            template_context.update({
                'background_image': tmp_bg,
                'deceased_image': tmp_deceased,
                'logo': tmp_logo
            })

            # Générer le HTML
            html_string = render_to_string('pdf/thank_you_note.html', template_context)
            html_path = os.path.join(tmpdirname, 'output.html')
            
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_string)
            try:
                # Générer le PDF
                pdf_buffer = BytesIO()
                HTML(filename=html_path, base_url=tmpdirname).write_pdf(
                    pdf_buffer,
                    presentational_hints=True,
                    optimize_size=('fonts', 'images'),
                )
                pdf = pdf_buffer.getvalue()
            finally:
                if os.path.exists(html_path):
                    os.unlink(html_path)
                pdf_buffer.close()
                
            return pdf

    except Exception as e:
        print(f"Error generating PDF: {e}")
        raise


def substitute_variables(text, context):
    """
    Remplace les variables dans le texte avec leur valeur correspondante du contexte
    """
    replacements = {
        '[guest_name]': context.get('guest_name', 'Guest'),
        '[guest_address]': context.get('guest_address', ''),
        '[guest_email]': context.get('guest_email', ''),
        '[deceased_name]': context.get('deceased_name', ''),
        '[book_purchaser_name]': context.get('book_purchaser_name', ''),
        '[your_name]': context.get('book_purchaser_name', '')
    }
    
    for key, value in replacements.items():
        text = text.replace(key, value)
    
    return text


def send_thank_you_email(to_email, subject, context, book_purchase, guest_info):
    """
    Envoie un email de remerciement avec le PDF personnalisé
    """
    # Générer l'email HTML
    context['logo_url'] = f'{settings.BASE_URL}{staticfiles_storage.url("images/logo.png")}'
    context['guest_id'] = guest_info.id
    email_html_message = render_to_string('email/send_thank_you_guest.html', context)
    email_plaintext_message = render_to_string('email/send_thank_you_guest.txt', context)
    
    # Générer le PDF personnalisé pour ce guest
    pdf_content = generate_thank_you_note_pdf(book_purchase, guest_info)
    if guest_info:
        guest_info.thank_you_pdf.save(f'thank_you_{guest_info.id}.pdf', ContentFile(pdf_content), save=True)

    try:
        msg = EmailMultiAlternatives(
            subject,
            email_plaintext_message,
            settings.DEFAULT_FROM_EMAIL,
            [to_email]
        )
        msg.attach_alternative(email_html_message, "text/html")
        msg.attach('thank_you_note.pdf', pdf_content, 'application/pdf')
        
        msg.send()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False