from visitationbook import settings
from visitationbookapi.models import *
from rest_framework.views import exception_handler
from rest_framework.response import Response
from django.core.files.base import ContentFile
from django.core.mail import EmailMultiAlternatives
from django.contrib.staticfiles.storage import staticfiles_storage
from django.db.models import QuerySet
from django.template.loader import render_to_string
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.platypus import Image as ReportLabImage
from PIL import Image as PILImage, ImageDraw
from functools import wraps
from io import BytesIO
from math import ceil
import os


def add_background_to_canvas(canvas, doc, background_image_path):
    canvas.saveState()
    # Calculer les dimensions pour couvrir toute la page
    page_width, page_height = letter
    canvas.drawImage(background_image_path, 0, 0, width=page_width,
                     height=page_height, preserveAspectRatio=True, mask='auto')
    canvas.restoreState()


def first_page(canvas, doc):
    background_image_path = getattr(doc, '_background_image_path', None)
    if background_image_path:
        add_background_to_canvas(canvas, doc, background_image_path)
    # Vous pouvez ajouter ici d'autres éléments spécifiques à la première page


def later_pages(canvas, doc):
    # Traitez ici les pages suivantes si nécessaire
    pass


def create_circular_image(image_path, size=(1*inch, 1*inch)):
    img = PILImage.open(image_path)
    img = img.convert("RGBA")
    img = img.resize((int(size[0]), int(size[1])), PILImage.LANCZOS)

    mask = PILImage.new('L', img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + img.size, fill=255)

    output = PILImage.new('RGBA', img.size, (255, 255, 255, 0))
    output.paste(img, (0, 0), mask)

    img_buffer = BytesIO()
    output.save(img_buffer, format='PNG')
    img_buffer.seek(0)

    return img_buffer.getvalue()


def generate_pdf(book_purchase):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            topMargin=0.5*inch, bottomMargin=0.5*inch)

    # Définir le chemin de l'image de fond
    doc._background_image_path = book_purchase.custom_cover.path if book_purchase.custom_cover else book_purchase.book.cover.path

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='CustomTitle',
                              parent=styles['Heading1'],
                              alignment=TA_CENTER,
                              fontSize=24,
                              spaceAfter=0.3*inch))
    styles.add(ParagraphStyle(name='Date',
                              parent=styles['Normal'],
                              alignment=TA_CENTER,
                              fontSize=14,
                              spaceAfter=0.1*inch))
    styles.add(ParagraphStyle(name='PageTitle',
                              parent=styles['Heading2'],
                              alignment=TA_CENTER,
                              fontSize=18,
                              spaceAfter=0.5*inch))
    story = []

    # First page
    if book_purchase.deceased_name:
        story.append(Spacer(1, 1*inch))  # Espace en haut de la page
        story.append(Paragraph(f"{book_purchase.deceased_name}", styles['CustomTitle']))
        story.append(Spacer(1, 0.5*inch))

    # Add deceased image
    if book_purchase.deceased_image:
        story.append(Image(book_purchase.deceased_image.path,
                     width=6*inch, height=6*inch, kind='proportional'))
    else:
        story.append(Spacer(1, 6*inch))  # Placeholder if no image

    story.append(Spacer(1, 0.5*inch))
    if book_purchase.date_of_birth:
        story.append(Paragraph(
            f"Born: {book_purchase.date_of_birth.strftime('%B %d, %Y')}", styles['Date']))
    if book_purchase.date_of_death:
        story.append(Paragraph(
            f"Passed: {book_purchase.date_of_death.strftime('%B %d, %Y')}", styles['Date']))

    story.append(PageBreak())

    # Guest notes pages
    guest_infos = book_purchase.guest_infos.all()
    cards_per_page = 4
    total_pages = ceil(len(guest_infos) / cards_per_page)

    for page in range(total_pages):
        # Ajouter le titre "Visitors" en haut de chaque page
        story.append(Paragraph("Visitors", styles['PageTitle']))
        
        start = page * cards_per_page
        end = start + cards_per_page
        page_guests = guest_infos[start:end]
        
        # Calculer la largeur disponible sur la page
        page_width = letter[0]
        margin = 1 * inch  # 1 pouce de marge de chaque côté
        available_width = page_width - (2 * margin)
        
        # Calculer l'espacement vertical entre les cards
        page_height = letter[1]
        total_vertical_space = page_height - (2 * margin) - 1*inch  # Soustraire l'espace pour le titre
        space_between_cards = total_vertical_space / (cards_per_page + 1)  # +1 pour avoir un espace uniforme

        for i, guest in enumerate(page_guests):
            # Determine image position (left for even, right for odd)
            image_on_left = i % 2 == 0

            # Create a card-like structure for each guest
            card_content = []

            # Guest picture (if allowed and exists)
            guest_image = None
            if book_purchase.allow_picture and guest.guest_picture:
                img_data = create_circular_image(guest.guest_picture.path)
                guest_image = ReportLabImage(BytesIO(img_data), width=1.5*inch, height=1.5*inch)

            # Guest information
            guest_info = []
            if book_purchase.allow_name and guest.guest_name:
                guest_info.append(
                    Paragraph(f"<b>{guest.guest_name}</b>", styles['Normal']))
            if book_purchase.allow_address and guest.guest_address:
                guest_info.append(
                    Paragraph(guest.guest_address, styles['Normal']))
            if book_purchase.allow_email and guest.guest_email:
                guest_info.append(
                    Paragraph(guest.guest_email, styles['Normal']))

            # Add custom fields
            if book_purchase.allow_special_notes and guest.special_notes:
                guest_info.append(
                    Paragraph(f"<i>{guest.special_notes}</i>", styles['Normal']))
            

            # Combine image and info based on position
            if image_on_left:
                card_content = [[guest_image or '', guest_info]]
                text_align = 'LEFT'
            else:
                card_content = [[guest_info, guest_image or '']]
                text_align = 'RIGHT'

            # Create a table for the card
            image_width = available_width / 3
            text_width = available_width * 2 / 3
            card_table = Table(card_content, colWidths=[image_width, text_width])
            card_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),  # Center the image
                ('ALIGN', (1, 0), (1, 0), text_align),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ]))

            # Add vertical spacing before card
            story.append(Spacer(1, space_between_cards))

            # Add left margin spacer, card table, and right margin spacer
            story.append(
                Table([[Spacer(margin, 1), card_table, Spacer(margin, 1)]],
                      colWidths=[margin, available_width, margin])
            )

        if page < total_pages - 1:
            story.append(PageBreak())

    # Last page (Thank you message)
    story.append(PageBreak())
    thank_you_message = """
    During this time of profound sorrow, we want you to know that our thoughts and
    hearts are with you. Losing someone so dear is never easy, and words often fall short
    in expressing the depth of our sympathy.
    
    Please accept our heartfelt gratitude for allowing us to be a part of honoring Pac
    Lee's memory. It has been a privilege to support you during this time, and we hope that
    our service provided some measure of comfort and peace.
    
    May you find strength in the cherished memories you hold and in the love that
    surrounds you.
    
    With deepest sympathy,
    """
    for line in thank_you_message.split('\n'):
        story.append(Paragraph(line.strip(), styles['Normal']))

    # Add logo
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.png')
    story.append(Spacer(1, 0.5*inch))
    try:
        story.append(Image(logo_path, width=1*inch,
                     height=1*inch, hAlign='CENTER'))
    except Exception as e:
        print(f"Erreur lors du chargement du logo : {e}")

    # Add website link
    story.append(Spacer(1, 0.25*inch))
    story.append(Paragraph("www.visitationbook.com", styles['Center']))

    doc.build(story, onFirstPage=first_page, onLaterPages=later_pages)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


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
        'login_url': "http://34.171.253.86:3000/",
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