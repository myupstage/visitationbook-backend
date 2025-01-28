import os
import uuid
import time
import mimetypes
from visitationbook.os.abstract import CoreModel
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from visitationbookapi.managers import UserManager
from visitationbookapi.utils import *
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.utils import timezone

class User(AbstractUser, CoreModel):
    def _generate_document_path(self, filename):
        # Save original file name in model
        self.original_file_name = filename

        # Get new file name/upload path
        base, ext = os.path.splitext(filename)
        newname = "%s%s" % (uuid.uuid4(), ext)

        return os.path.join('{}'.format("profile_images"), newname)
    username = models.CharField(
        _('username'),
        max_length=150,
        # unique=True,
        help_text=_(
            'Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'),
        # validators=[AbstractUser.username_validator],
        # error_messages={
        #     'unique': _("A user with that username already exists."),
        # },
        default='',  # Ajout d'une valeur par défaut vide
    )
    full_name = models.CharField(verbose_name="Full Name", max_length=255, blank=True, null=True)
    address = models.CharField(verbose_name="Address", max_length=255, blank=True, null=True)
    email = models.EmailField(_('Email Address'), unique=True)
    security_question = models.CharField(verbose_name="Security Question", max_length=255, blank=True, null=True)
    security_answer = models.CharField(verbose_name="Security Question Answer", max_length=255, blank=True, null=True)
    name_funeral_home = models.CharField(verbose_name="Name of Funeral Home", max_length=255, blank=True, null=True)
    phone = models.CharField(verbose_name="Phone Number", max_length=255, blank=True, null=True)
    profile_image = models.ImageField(upload_to=_generate_document_path, blank=True, null=True)
    original_file_name = models.CharField(max_length=255, null=True, blank=True, help_text="Original file name")
    content_type = models.CharField(max_length=255, null=True, blank=True, help_text="The file extension")
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    
    google_id = models.CharField(max_length=255, blank=True, null=True)
    facebook_id = models.CharField(max_length=255, blank=True, null=True)
    social_avatar = models.URLField(max_length=500, blank=True, null=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']
    
    objects = UserManager()
    
    def get_active_subscription(self, book_type=None):
        """
        Récupère l'abonnement actif de l'utilisateur pour un type de livre spécifique
        Si book_type n'est pas spécifié, retourne tout abonnement actif
        """
        now = timezone.now()
        subscriptions = self.subscriptions.filter(
            is_active=True,
            end_date__gt=now
        )
        
        if book_type:
            subscriptions = subscriptions.filter(plan__book_type=book_type)
        
        return subscriptions.first()

    def get_all_subscriptions(self):
        """
        Récupère tous les abonnements de l'utilisateur, ordonnés par date de début
        """
        return self.subscriptions.all().order_by('-start_date')
    
    def __str__(self):
        return self.email
    
    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.email
        if self.profile_image and hasattr(self.profile_image, 'file'):
            self.original_file_name = self.profile_image.name
            mime_type, _ = mimetypes.guess_type(self.profile_image.name)
            self.content_type = mime_type
        super(User, self).save(*args, **kwargs)

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        ordering = ('email', 'full_name')


class Book(CoreModel):
    def _generate_document_path(self, filename):
        # Save original file name in model
        self.original_file_name = filename

        # Get new file name/upload path
        base, ext = os.path.splitext(filename)
        newname = "%s%s" % (uuid.uuid4(), ext)

        return os.path.join('{}'.format("book_covers"), newname)
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, verbose_name="Title")
    cover = models.ImageField(verbose_name="Cover Image", null=True, blank=True, upload_to=_generate_document_path)
    original_file_name = models.CharField(max_length=255, null=True, blank=True, help_text="Original file name")
    content_type = models.CharField(max_length=255, null=True, blank=True, help_text="The file extension")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Price")
    text_color = models.CharField(max_length=7, default="#000000", help_text="Color code in hex format (e.g. #ffffff)")

    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if self.cover and hasattr(self.cover, 'file'):
            mime_type, _ = mimetypes.guess_type(self.cover.name)
            self.content_type = mime_type
        super(Book, self).save(*args, **kwargs)

    class Meta:
        verbose_name_plural = "Books"
        verbose_name = "Book"
        ordering = ['title', 'price']


class PaymentMethod(CoreModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payment_methods")
    stripe_payment_method_id = models.CharField(max_length=255, null=True, blank=True)
    card_brand = models.CharField(max_length=50, verbose_name=_("Card Brand"), null=True, blank=True)
    last4 = models.CharField(max_length=4, verbose_name=_("Last 4 digits"), null=True, blank=True)
    expiry_month = models.IntegerField(verbose_name=_("Expiry Month"), null=True)
    expiry_year = models.IntegerField(verbose_name=_("Expiry Year"), null=True)
    card_holder = models.CharField(max_length=255, verbose_name=_("Card Holder"), null=True, blank=True)
    is_default = models.BooleanField(default=False, verbose_name=_("Is Default"))
    added_on = models.DateTimeField(auto_now_add=True, verbose_name=_("Added On"), null=True)

    def __str__(self):
        return f'{self.card_brand} ****{self.last4}'

    class Meta:
        verbose_name_plural = "Payment Methods"
        verbose_name = "Payment Method"
        ordering = ['-is_default', 'expiry_year', 'expiry_month']
        

class PaymentTransaction(CoreModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payment_transactions")
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True, related_name="transactions")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Amount"))
    tax = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Tax"))
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name=_("Discount"))
    total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Total"))
    payment_date = models.DateTimeField(auto_now_add=True, verbose_name=_("Payment Date"))
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed')], verbose_name=_("Payment Status"))
    stripe_payment_intent_id = models.CharField(max_length=1000, blank=True, null=True)

    def __str__(self):
        return f"Transaction {self.id} - {self.status} - {self.total}"

    class Meta:
        verbose_name_plural = "Payment Transactions"
        verbose_name = "Payment Transaction"
        ordering = ['-payment_date']


class SubscriptionPlan(CoreModel):
    """Modèle pour les différents plans d'abonnement disponibles"""
    PLAN_TYPES = [
        ('small', 'Small Funeral Home'),
        ('medium', 'Medium Size Funeral Home'),
        ('large', 'Large Funeral Home'),
    ]
    
    BOOK_TYPES = [
        ('visitation', 'Visitation Book Only'),
        ('obituary', 'Obituary Book Only'),
        ('both', 'Both Books'),
    ]

    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES)
    book_type = models.CharField(max_length=20, choices=BOOK_TYPES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    max_books = models.IntegerField(help_text="Maximum number of books allowed")
    duration_months = models.IntegerField(default=12)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    stripe_price_id = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.name} - {self.get_plan_type_display()} ({self.get_book_type_display()})"

    class Meta:
        unique_together = ('plan_type', 'book_type')
        ordering = ['plan_type', 'book_type']


class SubscriptionFeature(CoreModel):
    """Caractéristiques spécifiques de chaque plan"""
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE, related_name='features')
    name = models.CharField(max_length=100)
    description = models.TextField()
    
    def __str__(self):
        return f"{self.plan.name} - {self.name}"


class FuneralHomeSubscription(CoreModel):
    """Abonnements actifs des pompes funèbres"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    auto_renew = models.BooleanField(default=True)
    
    # Payment tracking
    stripe_subscription_id = models.CharField(max_length=1000, blank=True, null=True)
    payment_transaction = models.ForeignKey(PaymentTransaction, on_delete=models.SET_NULL, null=True, blank=True, related_name="subscriptions")
    latest_invoice_id = models.CharField(max_length=1000, blank=True, null=True)
    
    books_created = models.IntegerField(default=0, help_text="Number of books created under this subscription")
    
    def is_valid(self):
        return (
            self.is_active and 
            self.end_date > timezone.now() and 
            self.books_created < self.plan.max_books
        )
    
    def can_create_book(self):
        return self.is_valid() and self.books_created < self.plan.max_books
    
    def increment_books_count(self):
        if self.can_create_book():
            self.books_created += 1
            self.save(update_fields=['books_created'])
            return True
        return False

    def __str__(self):
        return f"{self.user.full_name} - {self.plan.name}"
        
    class Meta:
        ordering = ['-start_date']        


class BookPurchase(CoreModel):
    def _generate_deceased_image_path(self, filename):
        # Get new file name/upload path
        base, ext = os.path.splitext(filename)
        newname = "%s%s" % (uuid.uuid4(), ext)
        
        # Créer le répertoire s'il n'existe pas
        directory = 'deceased_images'
        path = os.path.join(settings.MEDIA_ROOT, directory)
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)

        return os.path.join(directory, newname)

    def _generate_custom_cover_path(self, filename):
        # Get new file name/upload path
        base, ext = os.path.splitext(filename)
        newname = "%s%s" % (uuid.uuid4(), ext)
        
        # Créer le répertoire s'il n'existe pas
        directory = 'custom_book_covers'
        path = os.path.join(settings.MEDIA_ROOT, directory)
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)

        return os.path.join(directory, newname)
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='book_purchases', verbose_name="User")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='purchases', verbose_name="Book")
    custom_cover = models.ImageField(upload_to=_generate_custom_cover_path, verbose_name="Custom Cover Image", blank=True, null=True, help_text="User's custom cover if provided")
    custom_text_color = models.CharField(max_length=7, default="#000000", help_text="Color code in hex format (e.g. #ffffff)")
    payment_status = models.BooleanField(default=False, verbose_name="Payment Status")
    purchase_date = models.DateTimeField(auto_now_add=True, verbose_name="Purchase Date")
    
    payment_transaction = models.ForeignKey(PaymentTransaction, on_delete=models.SET_NULL, null=True, blank=True, related_name="book_purchases", verbose_name="Payment Transaction")
    
    # Deceased Info Fields
    deceased_image = models.ImageField(upload_to=_generate_deceased_image_path, verbose_name="Deceased Image", null=True, blank=True)
    deceased_name = models.CharField(max_length=255, verbose_name="Deceased Name", null=True, blank=True)
    date_of_birth = models.DateField(verbose_name="Date of Birth", null=True, blank=True)
    date_of_death = models.DateField(verbose_name="Date of Death", null=True, blank=True)
    
    # Guest Info Options Fields
    allow_picture = models.BooleanField(default=False, verbose_name="Allow guest to add a picture to their name")
    allow_name = models.BooleanField(default=True, verbose_name="Allow guest to add their name")
    allow_address = models.BooleanField(default=True, verbose_name="Allow guest to add their address")
    allow_email = models.BooleanField(default=True, verbose_name="Allow guest to add their email")
    allow_special_notes = models.BooleanField(default=False, verbose_name="Allow special notes to the family")
    
    # Is both checking
    obituary = models.OneToOneField('Obituary', on_delete=models.SET_NULL, null=True, blank=True, related_name="book_purchase", verbose_name="Obituary")
    is_both = models.BooleanField(default=False, verbose_name="Is both checking")
    
    # PDF File Generation
    pdf_file = models.FileField(upload_to='book_purchase_pdfs/', null=True, blank=True)
    is_complete = models.BooleanField(default=False, verbose_name="Is complete checking")
    
    # Guest Visit Count
    visit_count = models.PositiveIntegerField(default=0, verbose_name="Visit Count")
    
    attending_note = models.TextField(verbose_name="Attending Note", blank=True, null=True, help_text="HTML formatted thank you message from the book purchaser")
    attending_note_pdf = models.FileField(upload_to='book_purchase_attending_note_pdfs/', null=True, blank=True)
    
    subscription = models.ForeignKey(FuneralHomeSubscription, on_delete=models.SET_NULL, null=True, blank=True, related_name='book_purchases')

    def check_completion(self):
        if all([self.deceased_name, self.deceased_image, self.date_of_death]):
            self.is_complete = True
        else:
            self.is_complete = False

    def generate_initial_pdf(self):
        if not self.pdf_file and self.is_complete:
            try:
                # Attendre un court instant pour s'assurer que les fichiers sont bien sauvegardés
                time.sleep(0.5)
                update_pdf(self)
            except Exception as e:
                print(f"Error generating PDF for book_purchase {self.id}: {e}")
            
    def delete_existing_pdf(self):
        if self.pdf_file:
            if os.path.isfile(self.pdf_file.path):
                os.remove(self.pdf_file.path)
            self.pdf_file = None
            self.save()
    
    def delete_existing_attending_note_pdf(self):
        """Supprime le fichier PDF existant s'il existe"""
        if self.attending_note_pdf:
            if os.path.isfile(self.attending_note_pdf.path):
                os.remove(self.attending_note_pdf.path)
            self.attending_note_pdf = None
    
    def generate_attending_note_pdf(self):
        """Génère le PDF template de la note de remerciement"""
        if not self.attending_note:
            return False

        try:
            # Générer le PDF template (sans guest_info)
            pdf_content = generate_thank_you_note_pdf(self)
            
            # Supprimer l'ancien PDF
            self.delete_existing_attending_note_pdf()
            
            # Sauvegarder le nouveau PDF
            pdf_filename = f'attending_note_{self.id}.pdf'
            self.attending_note_pdf.save(
                pdf_filename,
                ContentFile(pdf_content),
                save=False
            )
            
            # Mettre à jour uniquement le champ PDF
            BookPurchase.objects.filter(id=self.id).update(
                attending_note_pdf=self.attending_note_pdf.name
            )
            
            return True
            
        except Exception as e:
            print(f"Error generating attending note PDF template for book_purchase {self.id}: {e}")
            return False
            
    def increment_visit_count(self):
        self.visit_count += 1
        self.save(update_fields=['visit_count'])
            
    def save(self, *args, generate_pdf=True, generate_attending_note_pdf=True, **kwargs):
        # Déterminer si c'est une création ou une modification
        is_new = self._state.adding
        
        if is_new and self.subscription:
            if not self.subscription.can_create_book():
                raise ValidationError("Subscription limit reached or expired")
            self.subscription.increment_books_count()
            
            # Si c'est via un abonnement, pas besoin de paiement
            self.payment_status = True
        
        # Sauvegarder les anciennes valeurs pour comparaison
        if not is_new:
            old_attending_note = BookPurchase.objects.get(pk=self.pk).attending_note
        else:
            old_attending_note = None

        # Vérifier si l'état est complet
        self.check_completion()
        
        # Sauvegarder l'instance
        super().save(*args, **kwargs)

        # Générer le PDF principal si nécessaire
        if generate_pdf and self.is_complete and not is_new:
            self.generate_initial_pdf()

        # Générer le PDF de la note de remerciement si nécessaire
        if generate_attending_note_pdf and self.attending_note:
            # Vérifier si la note a changé
            if old_attending_note != self.attending_note:
                self.generate_attending_note_pdf()

    def __str__(self):
        return f"{self.user.email} - {self.book.title} - {'Paid' if self.payment_status else 'Pending'}"

    class Meta:
        verbose_name_plural = "Book Purchases"
        verbose_name = "Book Purchase"
        ordering = ['-purchase_date']

        
class GuestInfo(CoreModel):
    def _generate_guest_picture_path(self, filename):
        # Get new file name/upload path
        base, ext = os.path.splitext(filename)
        newname = "%s%s" % (uuid.uuid4(), ext)
        return os.path.join('{}'.format("guest_pictures"), newname)
    
    def _generate_thank_you_pdfs_path(self, filename):
        # Get new file name/upload path
        base, ext = os.path.splitext(filename)
        newname = "%s%s" % (uuid.uuid4(), ext)
        return os.path.join('{}'.format("thank_you_pdfs"), newname)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    book_purchase = models.ForeignKey(BookPurchase, on_delete=models.CASCADE, related_name='guest_infos', verbose_name="Book Purchase")
    guest_picture = models.ImageField(upload_to=_generate_guest_picture_path, verbose_name="Guest Picture", blank=True, null=True, help_text="Guest's Picture if required")
    guest_name = models.CharField(max_length=255, verbose_name="Guest Name", blank=True, null=True)
    guest_address = models.CharField(max_length=255, verbose_name="Guest Address", blank=True, null=True)
    guest_email = models.EmailField(verbose_name="Guest Email", blank=True, null=True)
    special_notes = models.TextField(verbose_name="Special Notes to the Family", blank=True, null=True)
    thank_you_pdf = models.FileField(upload_to=_generate_thank_you_pdfs_path, verbose_name="Guest Thank You PDF", blank=True, null=True)

    def __str__(self):
        return self.guest_name if self.guest_name else "Guest Info"

    class Meta:
        verbose_name_plural = "Guest Infos"
        verbose_name = "Guest Info"
        ordering = ['-created_at']
        
        
class Obituary(CoreModel):
    def _generate_document_path(self, filename):
        # Get new file name/upload path
        base, ext = os.path.splitext(filename)
        newname = "%s%s" % (uuid.uuid4(), ext)

        return os.path.join('{}'.format("obituaries_pdfs"), newname)
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='obituaries')
    deceased_name = models.CharField(max_length=255, verbose_name="Deceased Name")
    book_cover = models.ImageField(upload_to='obituary_covers/', verbose_name="Book Cover", null=True, blank=True)
    obituary_pdf = models.FileField(upload_to=_generate_document_path, verbose_name="Obituary PDF", null=True, blank=True)
    is_both = models.BooleanField(default=False, verbose_name="Is both checking")
    visit_count = models.PositiveIntegerField(default=0, verbose_name="Visit Count")
    text_color = models.CharField(max_length=7, default="#000000", help_text="Color code in hex format (e.g. #ffffff)")
    
    def increment_visit_count(self):
        self.visit_count += 1
        self.save(update_fields=['visit_count'])

    def __str__(self):
        return f"Obituary of {self.deceased_name}"

    class Meta:
        verbose_name_plural = "Obituaries"
        verbose_name = "Obituary"
        ordering = ['-created_at']
        
        
