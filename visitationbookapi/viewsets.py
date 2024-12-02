from django.db import transaction
from django.contrib.auth.models import User
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from visitationbookapi.models import *
from visitationbookapi.serializers import *
from visitationbookapi.permissions import *
from visitationbookapi.utils import *
from django_filters.rest_framework import DjangoFilterBackend
from decimal import Decimal
import stripe
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from email.mime.image import MIMEImage
from django.contrib.staticfiles.storage import staticfiles_storage


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    search_fields = ['full_name', 'email']
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    ordering_fields = ['full_name']
    filterset_fields = {
        'id': ['exact'],
        'full_name': ['icontains', 'exact'],
        'email': ['icontains', 'exact'],
    }
    http_method_names = ['get', 'put', 'head', 'options', 'trace']


class BookViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]


class BookPurchaseViewSet(viewsets.ModelViewSet):
    queryset = BookPurchase.objects.all()
    serializer_class = BookPurchaseSerializer
    permission_classes = [BookPurchasePermission]
    authentication_classes = [JWTAuthentication]
    
    def get_serializer_class(self):
        if self.action == 'retrieve' and (not self.request.user.is_authenticated or self.get_object().user != self.request.user):
            return BookPurchaseSerializerLimited
        return BookPurchaseSerializer

    def get_queryset(self):
        if self.action == 'list' and self.request.user.is_authenticated:
            return BookPurchase.objects.filter(user=self.request.user)
        return BookPurchase.objects.all()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required to list book purchases."},
                            status=status.HTTP_403_FORBIDDEN)
        return super().list(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        self.perform_update(serializer)
        instance.check_completion()  # Vérifier si toutes les étapes sont complètes

        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def process_payment(self, request, pk=None):
        try:
            book_purchase = self.get_object()
        except BookPurchase.DoesNotExist:
            return Response({"error": "BookPurchase not found."}, status=status.HTTP_404_NOT_FOUND)
        
        payment_method_id = request.data.get('payment_method_id')
        
        if not payment_method_id:
            return Response({"error": "Payment method ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payment_method = PaymentMethod.objects.get(id=payment_method_id, user=request.user)
        except PaymentMethod.DoesNotExist:
            return Response({"error": "Invalid payment method."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = book_purchase.book.price
            tax = Decimal(amount) * Decimal('0.15')
            discount = Decimal('0.00')
            total = amount + tax - discount

            intent = stripe.PaymentIntent.create(
                amount=int(total * 100),
                currency='usd',
                customer=request.user.stripe_customer_id,
                payment_method=payment_method.stripe_payment_method_id,
                off_session=True,
                confirm=True,
            )

            book_purchase.payment_status = True
            book_purchase.save()

            payment_transaction = PaymentTransaction.objects.create(
                user=request.user,
                payment_method=payment_method,
                amount=amount,
                tax=tax,
                discount=discount,
                total=total,
                status='completed',
                stripe_payment_intent_id=intent.id
            )

            book_purchase.payment_transaction = payment_transaction
            book_purchase.save()
            
            send_payment_confirmation_email(request.user, book_purchase)

            return Response({"success": True, "message": "Payment processed successfully."}, status=status.HTTP_200_OK)

        except stripe.error.CardError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def perform_create(self, serializer):
        if self.request.user and self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
        else:
            raise permissions.PermissionDenied("User must be authenticated to create a book purchase.")

    def perform_update(self, serializer):
        serializer.save()
        
    @action(detail=True, methods=['post'], permission_classes=[permissions.AllowAny], authentication_classes=[])
    def increment_visit(self, request, pk=None):
        try:
            book_purchase = self.get_object()
            
            if request.user.is_authenticated:
                if book_purchase.user == request.user:
                    return Response({"message": "Visite du propriétaire, compteur non incrémenté", "visit_count": book_purchase.visit_count}, status=status.HTTP_200_OK)
                
            book_purchase.increment_visit_count()
            return Response({"visit_count": book_purchase.visit_count}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GuestInfoViewSet(viewsets.ModelViewSet):
    queryset = GuestInfo.objects.all()
    serializer_class = GuestInfoSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def perform_create(self, serializer):
        guest_info = serializer.save()
        book_purchase = guest_info.book_purchase
        if book_purchase.is_complete:
            update_pdf(book_purchase)

    def perform_update(self, serializer):
        guest_info = serializer.save()
        book_purchase = guest_info.book_purchase
        if book_purchase.is_complete:
            update_pdf(book_purchase)
        

class PaymentMethodViewSet(viewsets.ModelViewSet):
    """
    ViewSet permettant aux utilisateurs d'ajouter et de gérer leurs moyens de paiement.
    """
    queryset = PaymentMethod.objects.all()
    serializer_class = PaymentMethodSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    http_method_names = ['get', 'delete', 'head', 'options', 'trace', 'post']

    def get_queryset(self):
        if self.request.user and self.request.user.is_authenticated:
            return self.queryset.filter(user=self.request.user)
        else:
            return Response({"detail": "Authentication credentials were not provided."}, status=status.HTTP_401_UNAUTHORIZED)

    def perform_create(self, serializer):
        if self.request.user and self.request.user.is_authenticated:
            serializer.save()
        else:
            raise permissions.PermissionDenied("User must be authenticated to create a book purchase.")


class PaymentTransactionViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les transactions de paiement des utilisateurs.
    """
    queryset = PaymentTransaction.objects.all()
    serializer_class = PaymentTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    http_method_names = ['get', 'delete', 'head', 'options', 'trace']

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Response({"detail": "Authentication credentials were not provided."}, status=status.HTTP_401_UNAUTHORIZED)
        return PaymentTransaction.objects.filter(user=self.request.user)

    @transaction.atomic
    def perform_create(self, serializer):
        user = self.request.user
        payment_method = serializer.validated_data.get('payment_method')
        total = serializer.validated_data.get('total')

        if not payment_method:
            return Response({"error": "No valid means of payment found."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Creating a PaymentIntent with Stripe
            intent = stripe.PaymentIntent.create(
                amount=int(total * 100),  # Stripe uses cents
                currency='usd',
                customer=user.stripe_customer_id,
                payment_method=payment_method.stripe_payment_method_id,
                off_session=True,
                confirm=True,
            )

            # Register transaction
            transaction = serializer.save(
                user=user,
                status='completed' if intent.status == 'succeeded' else 'pending',
                stripe_payment_intent_id=intent.id
            )

            return Response({
                "message": "Payment successfully processed",
                "transaction_id": transaction.id,
                "status": transaction.status
            }, status=status.HTTP_201_CREATED)

        except stripe.error.CardError as e:
            # Card error, e.g. insufficient funds
            err = e.error
            return Response({
                "error": f"Card error: {err.message}",
                "code": err.code
            }, status=status.HTTP_400_BAD_REQUEST)

        except stripe.error.StripeError as e:
            # For other Stripe errors
            return Response({"error": "An error has occurred during payment processing."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            # For any other unexpected error
            return Response({"error": "An unexpected error has occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        
class ObituaryViewSet(viewsets.ModelViewSet):
    queryset = Obituary.objects.all()
    serializer_class = ObituarySerializer
    permission_classes = [ObituaryPermission]
    authentication_classes = [JWTAuthentication]

    def get_queryset(self):
        if self.action == 'list' and self.request.user.is_authenticated:
            return Obituary.objects.filter(user=self.request.user)
        return Obituary.objects.all()

    def list(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required to list obituaries."},
                            status=status.HTTP_403_FORBIDDEN)
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
        else:
            raise permissions.PermissionDenied("User must be authenticated to create an obituary.")

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()     
        if instance.user != request.user:
            return Response({"detail": "You do not have permission to update this obituary."}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)

    def perform_update(self, serializer):
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user != request.user:
            return Response({"detail": "You do not have permission to delete this obituary."},
                            status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.AllowAny], authentication_classes=[])
    def increment_visit(self, request, pk=None):
        try:
            obituary = self.get_object()
            
            if request.user.is_authenticated:
                if obituary.user == request.user:
                    return Response({"message": "Visite du propriétaire, compteur non incrémenté", "visit_count": obituary.visit_count}, status=status.HTTP_200_OK)
                    
            obituary.increment_visit_count()
            return Response({"visit_count": obituary.visit_count}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class EmailViewSet(viewsets.ViewSet):
    """
    A simple ViewSet to send emails.
    """
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    
    def create(self, request):
        serializer = EmailSerializer(data=request.data)

        if serializer.is_valid():
            from_email = serializer.validated_data['from_email']
            emails_to = serializer.validated_data['emails_to']
            message = serializer.validated_data['message']
            custom_field_25 = serializer.validated_data.get('custom_field_25', False)
            custom_field_50 = serializer.validated_data.get('custom_field_50', False)
            custom_field_25_value = serializer.validated_data.get('custom_field_25_value', '')
            custom_field_50_value = serializer.validated_data.get('custom_field_50_value', '')
            special_note = serializer.validated_data['special_note']
            attachments = request.FILES.getlist('attachments')
            book_purchase_id = serializer.validated_data['book_purchase_id']
            
            book_purchase = BookPurchase.objects.get(id=book_purchase_id)
            if not book_purchase:
                return Response({"message": "Book Purchase ID is invalid"}, status=status.HTTP_403_FORBIDDEN)
            
            logo_url = f'{settings.BASE_URL}{staticfiles_storage.url("images/logo.png")}'
            
            url = "{}admin/visitation-books/send-guest?token={}".format(settings.FRONT_URL, book_purchase.id)
            subject = f"Thank you for attending note for {book_purchase.deceased_name}" if book_purchase.deceased_name != None else "Thank you for attending note"
                
            context = {
                'logo_url': logo_url,
                'url': url,
                'subject': subject,
                'message': message,
                'custom_field_25_value': custom_field_25_value if custom_field_25 and special_note else "",
                'custom_field_50_value': custom_field_50_value if custom_field_50 and special_note else "",
                'attachments': attachments
            }

            email_html_message = render_to_string('email/send_thank_you.html', context)
            email_plaintext_message = render_to_string('email/send_thank_you.txt', context)

            msg = EmailMultiAlternatives(
                subject,
                email_plaintext_message,
                from_email,
                emails_to
            )
            msg.attach_alternative(email_html_message, "text/html")
            
            if attachments:
                for attachment in attachments:
                    img_data = attachment.read()
                    msg_img = MIMEImage(img_data, _subtype=attachment.content_type.split('/')[1])
                    msg_img.add_header('Content-ID', f'<{attachment.name}>')
                    msg_img.add_header('Content-Disposition', 'inline', filename=attachment.name)
                    msg.attach(msg_img)
            
            try:
                msg.send()
                return Response({"message": "Email sent successfully"}, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
