import os
import uuid
import mimetypes
from visitationbook.os.abstract import CoreModel
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from visitationbookapi.managers import UserManager
from visitationbookapi.utils import *
from django.core.exceptions import ValidationError

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
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Transaction {self.id} - {self.status} - {self.total}"

    class Meta:
        verbose_name_plural = "Payment Transactions"
        verbose_name = "Payment Transaction"
        ordering = ['-payment_date']
        

class BookPurchase(CoreModel):
    def _generate_custom_cover_path(self, filename):
        # Get new file name/upload path
        base, ext = os.path.splitext(filename)
        newname = "%s%s" % (uuid.uuid4(), ext)

        return os.path.join('{}'.format("custom_book_covers"), newname)
    
    def _generate_deceased_image_path(self, filename):
        # Get new file name/upload path
        base, ext = os.path.splitext(filename)
        newname = "%s%s" % (uuid.uuid4(), ext)

        return os.path.join('{}'.format("deceased_images"), newname)
    
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
    
    obituary = models.OneToOneField('Obituary', on_delete=models.SET_NULL, null=True, blank=True, related_name="book_purchase", verbose_name="Obituary")
    
    is_both = models.BooleanField(default=False, verbose_name="Is both checking")
    
    pdf_file = models.FileField(upload_to='book_purchase_pdfs/', null=True, blank=True)
    is_complete = models.BooleanField(default=False, verbose_name="Is complete checking")
    
    visit_count = models.PositiveIntegerField(default=0, verbose_name="Visit Count")

    def check_completion(self):
        if all([self.deceased_name, self.deceased_image, self.date_of_death]):
            self.is_complete = True
            self.generate_initial_pdf()
        else:
            self.is_complete = False

    def generate_initial_pdf(self):
        if not self.pdf_file:
            update_pdf(self)
            
    def delete_existing_pdf(self):
        if self.pdf_file:
            if os.path.isfile(self.pdf_file.path):
                os.remove(self.pdf_file.path)
            self.pdf_file = None
            self.save()
            
    def increment_visit_count(self):
        self.visit_count += 1
        self.save(update_fields=['visit_count'])
            
    def save(self, *args, **kwargs):
        self.check_completion()
        super().save(*args, **kwargs)

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

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    book_purchase = models.ForeignKey(BookPurchase, on_delete=models.CASCADE, related_name='guest_infos', verbose_name="Book Purchase")
    guest_picture = models.ImageField(upload_to=_generate_guest_picture_path, verbose_name="Guest Picture", blank=True, null=True, help_text="Guest's Picture if required")
    guest_name = models.CharField(max_length=255, verbose_name="Guest Name", blank=True, null=True)
    guest_address = models.CharField(max_length=255, verbose_name="Guest Address", blank=True, null=True)
    guest_email = models.EmailField(verbose_name="Guest Email", blank=True, null=True)
    special_notes = models.TextField(verbose_name="Special Notes to the Family", blank=True, null=True)

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
        
        
