from django.contrib import admin
from visitationbookapi.models import *
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from import_export.admin import ImportExportModelAdmin, ImportMixin, ExportMixin

admin.site.site_header = "VisitationBook"
admin.site.site_title = "VisitationBook Admin"


@admin.register(User)
class UserAdmin(ExportMixin, ImportMixin, BaseUserAdmin):
    """Define admin model for custom User model with no email field."""

    fieldsets = (
        (None, {'fields': ('username', 'email', 'password', 'profile_image')}),
        (_('Personal info'), {'fields': ('full_name', 'address', 'security_question', 'security_answer', 'stripe_customer_id')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )
    list_display = ('id', 'username', 'email', 'full_name', 'address', 'is_staff', 'is_superuser',)
    search_fields = ('email', 'full_name', 'address')
    ordering = ('id',)
    list_display_links = ['email']
    list_filter = ['is_staff', 'is_superuser', 'is_active']


@admin.register(Book)
class BookAdmin(ImportExportModelAdmin):
    list_display = ('id', 'title', 'price', 'original_file_name', 'text_color')
    search_fields = ('id', 'title', 'text_color')
    readonly_fields = ('id', 'content_type', 'original_file_name')

@admin.register(PaymentMethod)
class PaymentMethodAdmin(ImportExportModelAdmin):
    list_display = ('id', 'user', 'card_holder', 'card_brand', 'last4', 'is_default')
    search_fields = ('id', 'user__email', 'card_holder', 'card_brand', 'last4')
    readonly_fields = ('id',)

@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(ImportExportModelAdmin):
    list_display = ('id', 'user', 'amount', 'status', 'total', 'payment_date')
    search_fields = ('id', 'user__email', 'status')
    readonly_fields = ('id', 'payment_date')

@admin.register(BookPurchase)
class BookPurchaseAdmin(ImportExportModelAdmin):
    list_display = ('id', 'deceased_name', 'user', 'book', 'purchase_date', 'payment_status', 'subscription_info')
    list_filter = ('payment_status', 'is_complete', 'subscription__plan__plan_type')
    search_fields = ('id', 'deceased_name', 'user__email', 'book__title', 'purchase_date', 'payment_status', 'subscription__plan__name')
    readonly_fields = ('id', 'purchase_date')
    
    def subscription_info(self, obj):
        if obj.subscription:
            return f"{obj.subscription.plan.name} ({obj.subscription.plan.get_plan_type_display()})"
        return "-"
    subscription_info.short_description = "Subscription"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 
            'book',
            'subscription',
            'subscription__plan'
        )

@admin.register(GuestInfo)
class GuestInfoAdmin(ImportExportModelAdmin):
    list_display = ('id', 'book_purchase', 'guest_name', 'guest_email')
    search_fields = ('id', 'guest_name', 'guest_email')
    readonly_fields = ('id',)

@admin.register(Obituary)
class ObituaryAdmin(ImportExportModelAdmin):
    list_display = ('id', 'user', 'deceased_name', 'book_cover', 'obituary_pdf', 'is_both', 'text_color')
    search_fields = ('id', 'deceased_name', 'user__email', 'book_cover', 'obituary_pdf', 'is_both', 'text_color')
    readonly_fields = ('id',)


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(ImportExportModelAdmin):
    list_display = ('id', 'name', 'plan_type', 'book_type', 'price', 'max_books', 'duration_months', 'is_active')
    list_filter = ('plan_type', 'book_type', 'is_active')
    search_fields = ('name', 'description')
    readonly_fields = ('id',)


@admin.register(SubscriptionFeature)
class SubscriptionFeatureAdmin(ImportExportModelAdmin):
    list_display = ('id', 'plan', 'name', 'description')
    list_filter = ('plan__plan_type', 'plan__book_type')
    search_fields = ('name', 'description', 'plan__name')
    readonly_fields = ('id',)


@admin.register(FuneralHomeSubscription)
class FuneralHomeSubscriptionAdmin(ImportExportModelAdmin):
    list_display = ('id', 'user', 'plan', 'start_date', 'end_date', 'is_active', 'books_created', 'auto_renew')
    list_filter = ('is_active', 'auto_renew', 'plan__plan_type', 'plan__book_type')
    search_fields = ('user__email', 'user__full_name', 'stripe_subscription_id', 'plan__name')
    readonly_fields = ('id', 'start_date', 'stripe_subscription_id', 'latest_invoice_id', 'books_created')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'plan')

    def has_delete_permission(self, request, obj=None):
        # Empêcher la suppression si l'abonnement est actif
        if obj and obj.is_active:
            return False
        return super().has_delete_permission(request, obj)