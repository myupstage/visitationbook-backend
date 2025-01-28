from rest_framework import routers
from visitationbookapi.viewsets import *
from visitationbook import settings

if settings.DEBUG == True:
    router = routers.DefaultRouter()
else:
    router = routers.SimpleRouter()
    
router.register(r'users', UserViewSet, basename="users")
router.register(r'books', BookViewSet, basename='books')
router.register(r'book-purchases', BookPurchaseViewSet, basename='book_purchases')
router.register(r'guest-infos', GuestInfoViewSet, basename='guest_infos')
router.register(r'payment-methods', PaymentMethodViewSet, basename='payment_methods')
router.register(r'payment-transactions', PaymentTransactionViewSet, basename='payment_transactions')
router.register(r'obituaries', ObituaryViewSet, basename='obituaries')
router.register(r'emails', EmailViewSet, basename='email')
router.register(r'subscription-plans', SubscriptionPlanViewSet, basename='subscription_plans')
router.register(r'subscriptions', FuneralHomeSubscriptionViewSet, basename='subscriptions')
