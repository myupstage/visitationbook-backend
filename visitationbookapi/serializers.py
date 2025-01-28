from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from visitationbookapi.models import *
from visitationbookapi.utils import *
from django.utils import timezone
from decimal import Decimal
import datetime
import stripe


class FullURLFileField(serializers.FileField):
    def __init__(self, **kwargs):
        kwargs.setdefault('required', False)
        kwargs.setdefault('allow_null', True)
        super().__init__(**kwargs)

    def to_representation(self, value):
        if not value:
            return None
        return get_full_url(value.url)


class LoginSerializer(TokenObtainPairSerializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(style={'input_type': 'password'})
    
    def validate(self, attrs):
        # Override the username field to accept email
        username_field = self.username_field
        email = attrs.get("email", None)
        if email:
            attrs[username_field] = email
        return super().validate(attrs)

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims (like full_name, phone etc.)
        token['full_name'] = user.full_name
        token['email'] = user.email
        token['address'] = user.address
        token['phone'] = user.phone
        return token


class Authenticate(APIView):
    permission_classes = (IsAuthenticated,)


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for password change endpoint.
    """
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value


class SubscriptionFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionFeature
        fields = ['id', 'name', 'description']
        

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    features = SubscriptionFeatureSerializer(many=True, read_only=True)
    
    class Meta:
        model = SubscriptionPlan
        fields = ['id', 'name', 'plan_type', 'book_type', 'price', 'max_books', 'duration_months', 'description', 'is_active', 'features', 'stripe_price_id']
        

class FuneralHomeSubscriptionBasicSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer(read_only=True)
    
    class Meta:
        model = FuneralHomeSubscription
        fields = ['id', 'plan', 'start_date', 'end_date', 'is_active', 'stripe_subscription_id']
        

class UserSerializer(serializers.ModelSerializer):
    payment_methods = serializers.SerializerMethodField()
    payment_transactions = serializers.SerializerMethodField()
    book_purchases = serializers.SerializerMethodField()
    obituaries = serializers.SerializerMethodField()
    profile_image = FullURLFileField()
    active_subscriptions = serializers.SerializerMethodField()
    all_subscriptions = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        extra_kwargs = {
            'password': {'write_only': True, 'required': False}
        }
        fields = ('id', 'email', 'full_name', 'address', 'security_question', 'security_answer', 
                  'name_funeral_home', 'phone', 'password', 'profile_image', 'original_file_name', 'content_type',
                  'payment_methods', 'payment_transactions', 'book_purchases', 'obituaries', 'stripe_customer_id', 'active_subscriptions', 'all_subscriptions')
        
    def get_payment_methods(self, obj):
        payment_method = PaymentMethod.objects.filter(user=obj)
        return PaymentMethodSerializer(payment_method, many=True).data
    
    def get_payment_transactions(self, obj):
        payment_transaction = PaymentTransaction.objects.filter(user=obj)
        return PaymentTransactionSerializer(payment_transaction, many=True).data
    
    def get_book_purchases(self, obj):
        book_purchase = BookPurchase.objects.filter(user=obj)
        return BookPurchaseSerializer(book_purchase, many=True).data
    
    def get_obituaries(self, obj):
        obituary = Obituary.objects.filter(user=obj)
        return ObituarySerializer(obituary, many=True).data
    
    def get_active_subscriptions(self, obj):
        """Retourne les abonnements actifs pour chaque type de livre"""
        active_subs = {}
        for book_type, _ in SubscriptionPlan.BOOK_TYPES:
            subscription = obj.get_active_subscription(book_type)
            if subscription:
                active_subs[book_type] = FuneralHomeSubscriptionBasicSerializer(subscription).data
        return active_subs

    def get_all_subscriptions(self, obj):
        subscriptions = obj.get_all_subscriptions()
        return FuneralHomeSubscriptionBasicSerializer(subscriptions, many=True).data

    def validate_password(self, value):
        validate_password(value)
        return value
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class BookSerializer(serializers.ModelSerializer):
    cover = FullURLFileField()
    
    class Meta:
        model = Book
        fields = ['id', 'title', 'cover', 'original_file_name', 'content_type', 'price', 'text_color']
    
    def validate(self, data):
        if data.get('cover') and not data['cover'].name.endswith(('.png', '.jpg', '.jpeg')):
            raise serializers.ValidationError("Invalid file type for cover. Only PNG, JPG, JPEG are accepted.")
        return data
    

class PaymentMethodSerializer(serializers.ModelSerializer):
    def check_expiry_month(value):
        if not 1 <= int(value) <= 12:
            raise serializers.ValidationError("Invalid expiry month.")


    def check_expiry_year(value):
        today = datetime.datetime.now()
        if not int(value) >= today.year:
            raise serializers.ValidationError("Invalid expiry year.")
        
    stripe_payment_method_id = serializers.CharField(max_length=150, required=True)
    card_holder = serializers.CharField(max_length=150, required=True)
    last4 = serializers.CharField(max_length=4, required=True)
    card_brand = serializers.CharField(max_length=50, required=True)
    expiry_month = serializers.IntegerField(required=True, validators=[check_expiry_month])
    expiry_year = serializers.IntegerField(required=True, validators=[check_expiry_year])
    
    
    class Meta:
        model = PaymentMethod
        fields = ['id', 'stripe_payment_method_id', 'card_holder', 'last4',
                  'card_brand', 'expiry_month', 'expiry_year', 'is_default', 'added_on']
        
    def create(self, validated_data):
        user = self.context['request'].user
        validated_data.pop('user', None)
        payment_method = PaymentMethod.objects.create(user=user, **validated_data)
        return payment_method
    

class PaymentTransactionSerializer(serializers.ModelSerializer):
    payment_method_id = serializers.UUIDField(write_only=True)
    payment_method = PaymentMethodSerializer(read_only=True)
    
    class Meta:
        model = PaymentTransaction
        fields = ['id', 'payment_method_id', 'payment_method', 'amount', 'tax',
                  'discount', 'total', 'payment_date', 'status', 'stripe_payment_intent_id']
        
    def create(self, validated_data):
        user = self.context['request'].user
        payment_method_id = validated_data.pop('payment_method_id')

        try:
            payment_method = PaymentMethod.objects.get(id=payment_method_id, user=user)
        except PaymentMethod.DoesNotExist:
            raise serializers.ValidationError("The payment method selected is invalid or does not belong to the user.")

        payment_transaction = PaymentTransaction.objects.create(user=user, payment_method=payment_method, **validated_data)
        return payment_transaction


class ObituarySerializer(serializers.ModelSerializer):
    obituary_pdf = FullURLFileField(required=False)
    book_cover = FullURLFileField()
    
    class Meta:
        model = Obituary
        fields = ['id', 'deceased_name', 'book_cover', 'obituary_pdf', 'is_both', 'visit_count', 'text_color']
        read_only_fields = ['id', 'user', 'visit_count']
        extra_kwargs = {
            'deceased_name': {'required': False},
            'book_cover': {'required': False},
            'obituary_pdf': {'required': False},
        }
    
    def validate(self, data):
        method = self.context.get('request').method if self.context.get('request') else None
        if method == 'POST':
            required_fields = ['deceased_name', 'book_cover', 'obituary_pdf']
            for field in required_fields:
                if field not in data:
                    raise serializers.ValidationError(f"{field} is required for creating a new obituary.")
        return data
    
    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class FuneralHomeSubscriptionSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer(read_only=True)
    plan_id = serializers.UUIDField(write_only=True)
    remaining_books = serializers.SerializerMethodField()
    days_remaining = serializers.SerializerMethodField()
    payment_transaction = PaymentTransactionSerializer(read_only=True)
    payment_transaction_id = serializers.UUIDField(write_only=True, required=False)
    client_secret = serializers.SerializerMethodField()
    
    class Meta:
        model = FuneralHomeSubscription
        fields = ['id', 'plan', 'plan_id', 'start_date', 'end_date', 'is_active', 'auto_renew', 'stripe_subscription_id', 'books_created', 
                'remaining_books', 'days_remaining', 'payment_transaction', 'payment_transaction_id', 'client_secret']
        read_only_fields = ['start_date', 'end_date', 'stripe_subscription_id', 'books_created']
        
    def get_client_secret(self, obj):
        # Cette méthode sera appelée pour obtenir le client_secret
        # On peut le stocker temporairement dans l'instance
        return getattr(obj, '_client_secret', None)
        
    def get_remaining_books(self, obj):
        return obj.plan.max_books - obj.books_created
        
    def get_days_remaining(self, obj):
        if obj.end_date:
            now = timezone.now()
            if now < obj.end_date:
                return (obj.end_date - now).days
        return 0

    def validate(self, data):
        user = self.context['request'].user
        plan_id = data.get('plan_id')
        
        try:
            plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            raise serializers.ValidationError("Invalid or inactive subscription plan")
            
        # Vérifier si l'utilisateur a déjà un abonnement actif pour ce type de livre
        active_sub = FuneralHomeSubscription.objects.filter(
            user=user,
            plan__book_type=plan.book_type,
            is_active=True,
            end_date__gt=timezone.now()
        ).first()
        
        if active_sub:
            raise serializers.ValidationError(f"You already have an active subscription for {plan.get_book_type_display()}")
            
        return data

    def create(self, validated_data):
        user = self.context['request'].user
        plan = SubscriptionPlan.objects.get(id=validated_data['plan_id'])
        payment_method_id = self.context['request'].data.get('payment_method_id')
        
        if not payment_method_id:
            raise serializers.ValidationError("Payment method ID is required")
            
        try:
            payment_method = PaymentMethod.objects.get(id=payment_method_id, user=user)
        except PaymentMethod.DoesNotExist:
            raise serializers.ValidationError("Invalid payment method")
        
        if not plan.stripe_price_id:
            # Création du prix dans Stripe
            stripe_price = stripe.Price.create(
                unit_amount=int(plan.price * 100),  # Stripe utilise les centimes
                currency='usd',  # ou 'eur' selon votre devise
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

            # Mise à jour du plan avec le nouveau price_id
            plan.stripe_price_id = stripe_price.id
            plan.save()
        
        if not user.stripe_customer_id:
            try:
                # Créer un customer Stripe
                customer = stripe.Customer.create(
                    email=user.email,
                    name=user.full_name,
                    metadata={
                        'user_id': str(user.id)
                    }
                )
                user.stripe_customer_id = customer.id
                user.save()
            except stripe.error.StripeError as e:
                raise serializers.ValidationError(f"Error creating Stripe customer: {str(e)}")
            
        # Attacher la méthode de paiement au client
        stripe.PaymentMethod.attach(
            payment_method.stripe_payment_method_id,
            customer=user.stripe_customer_id,
        )
        
        # Définir comme méthode de paiement par défaut
        stripe.Customer.modify(
            user.stripe_customer_id,
            invoice_settings={
                'default_payment_method': payment_method.stripe_payment_method_id
            }
        )
        
        # Calculer end_date
        start_date = timezone.now()
        end_date = start_date + timezone.timedelta(days=30 * plan.duration_months)
        
        try:
            # Créer la souscription Stripe
            stripe_subscription = stripe.Subscription.create(
                customer=user.stripe_customer_id,
                items=[
                    {
                        'price': plan.stripe_price_id,
                        'quantity': 1
                    }
                ],
                payment_behavior='default_incomplete',  # Assurez-vous que c'est bien là
                payment_settings={
                    'payment_method_types': ['card'],
                    'save_default_payment_method': 'on_subscription'  # Ajoutez ceci
                },
                expand=['latest_invoice.payment_intent'],  # Important pour récupérer le client secret
                metadata={
                    'plan_id': str(plan.id),
                    'user_id': str(user.id)
                }
            )
            
            # Calculer les montants
            amount = plan.price
            tax = Decimal(amount) * Decimal('0.15')  # 15% de taxe comme dans BookPurchase
            total = amount + tax
            
            # Vérifier le statut du paiement
            payment_status = 'pending'  # Par défaut
            if stripe_subscription.latest_invoice.payment_intent:
                if stripe_subscription.latest_invoice.payment_intent.status == 'succeeded':
                    payment_status = 'completed'
                else:
                    payment_status = 'pending'
            
            # Créer la transaction de paiement
            payment_transaction = PaymentTransaction.objects.create(
                user=user,
                payment_method=payment_method,
                amount=amount,
                tax=tax,
                discount=Decimal('0.00'),
                total=total,
                status=payment_status,
                stripe_payment_intent_id=stripe_subscription.latest_invoice.payment_intent.id[:255]
            )
            
            # Créer l'abonnement local
            subscription = FuneralHomeSubscription.objects.create(
                user=user,
                plan=plan,
                start_date=start_date,
                end_date=end_date,
                stripe_subscription_id=stripe_subscription.id[:255],
                payment_transaction=payment_transaction,  # Lier la transaction
                latest_invoice_id=stripe_subscription.latest_invoice.id[:255]
            )
            
            # Stockez le client_secret temporairement dans l'instance
            if stripe_subscription.latest_invoice.payment_intent:
                subscription._client_secret = stripe_subscription.latest_invoice.payment_intent.client_secret
            
            # Envoyer l'email de confirmation comme pour les autres paiements
            send_subscription_confirmation_email(user, subscription)
            
            return subscription
            
        except stripe.error.StripeError as e:
            raise serializers.ValidationError(f"Stripe error: {str(e)}")
        
        except Exception as e:
            print("Full error:", str(e))
            if 'stripe_subscription' in locals():
                try:
                    stripe.Subscription.delete(stripe_subscription.id)
                except:
                    pass
            raise serializers.ValidationError(f"Error creating subscription: {str(e)}")
        

class BookPurchaseSerializer(serializers.ModelSerializer):
    book_id = serializers.UUIDField(write_only=True, required=False)
    obituary_id = serializers.UUIDField(write_only=True, required=False)
    book = BookSerializer(read_only=True)
    obituary = ObituarySerializer(read_only=True)
    payment_transaction = PaymentTransactionSerializer(read_only=True)
    guests = serializers.SerializerMethodField()
    custom_cover = FullURLFileField()
    deceased_image = FullURLFileField()
    pdf_file = FullURLFileField()
    attending_note = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    attending_note_pdf = FullURLFileField()
    subscription_id = serializers.UUIDField(write_only=True, required=False)
    subscription = FuneralHomeSubscriptionSerializer(read_only=True)

    class Meta:
        model = BookPurchase
        fields = ['id', 'book_id', 'book', 'obituary_id', 'obituary', 'custom_cover', 'custom_text_color', 'payment_status', 'purchase_date',
                  'payment_transaction', 'deceased_image', 'deceased_name', 'date_of_birth', 'date_of_death', 
                  'allow_picture', 'allow_name', 'allow_address', 'allow_email', 'allow_special_notes',
                  'guests', 'is_both', 'pdf_file', 'is_complete', 'visit_count', 'attending_note', 'attending_note_pdf', 'subscription', 'subscription_id']
        read_only_fields = ['purchase_date', 'user', 'payment_status', 'visit_count']
        
    def get_guests(self, obj):
        guest_info = GuestInfo.objects.filter(book_purchase=obj)
        return GuestInfoSerializer(guest_info, many=True).data
        
    def validate_custom_cover(self, value):
        if value and not value.name.lower().endswith(('.png', '.jpg', '.jpeg')):
            raise serializers.ValidationError("Invalid file type for custom cover.")
        return value

    def validate_deceased_image(self, value):
        if value and not value.name.lower().endswith(('.png', '.jpg', '.jpeg')):
            raise serializers.ValidationError("Invalid file type for deceased image.")
        return value

    def create(self, validated_data):
        book_id = validated_data.pop('book_id')
        obituary_id = validated_data.pop('obituary_id', None)
        user = self.context['request'].user
        
        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            raise serializers.ValidationError("Invalid book ID")

        subscription = FuneralHomeSubscription.objects.filter(
            user=user,
            plan__book_type__in=['both', 'visitation'],
            is_active=True,
            end_date__gt=timezone.now()
        ).first()

        if subscription and subscription.can_create_book():
            validated_data['payment_status'] = True
        
        book_purchase = BookPurchase.objects.create(
            book=book, 
            user=user,
            subscription=subscription,  # Sera None si pas d'abonnement
            **validated_data
        )
        
        # Gestion de l'obituary
        if obituary_id:
            try:
                obituary = Obituary.objects.get(id=obituary_id)
                book_purchase.obituary = obituary
                book_purchase.save()
            except Obituary.DoesNotExist:
                raise serializers.ValidationError("Invalid obituary ID")
        
        if subscription:
            subscription.increment_books_count()
        
        return book_purchase
    
    def update(self, instance, validated_data):
        obituary_id = validated_data.pop('obituary_id', None)
        instance = super().update(instance, validated_data)

        if obituary_id:
            try:
                obituary = Obituary.objects.get(id=obituary_id)
                instance.obituary = obituary
                instance.save()
            except Obituary.DoesNotExist:
                raise serializers.ValidationError("Invalid obituary ID")

        return instance


class BookPurchaseSerializerLimited(serializers.ModelSerializer):
    book = BookSerializer(read_only=True)
    obituary = ObituarySerializer(read_only=True)
    guests = serializers.SerializerMethodField()
    custom_cover = FullURLFileField()
    deceased_image = FullURLFileField()
    pdf_file = FullURLFileField()
    attending_note_pdf = FullURLFileField()

    class Meta:
        model = BookPurchase
        fields = ['id', 'book', 'obituary', 'custom_cover', 'custom_text_color', 'deceased_name', 'date_of_birth', 'date_of_death', 'deceased_image',
                  'allow_picture', 'allow_name', 'allow_address', 'allow_email', 'allow_special_notes', 'guests', 'pdf_file', 'is_complete', 'attending_note_pdf']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Remove sensitive fields
        sensitive_fields = ['payment_status', 'purchase_date', 'payment_transaction']
        for field in sensitive_fields:
            representation.pop(field, None)
        return representation
    
    def get_guests(self, obj):
        guest_info = GuestInfo.objects.filter(book_purchase=obj)
        return GuestInfoSerializer(guest_info, many=True).data
    
    
class GuestInfoSerializer(serializers.ModelSerializer):
    book_purchase_id = serializers.UUIDField(write_only=True)
    guest_picture = FullURLFileField()
    has_attending_note = serializers.SerializerMethodField()
    thank_you_pdf = FullURLFileField()
    
    class Meta:
        model = GuestInfo
        fields = ['id', 'book_purchase_id', 'guest_picture', 'guest_name', 'guest_address', 'guest_email', 'special_notes', 'has_attending_note', 'thank_you_pdf']
        read_only_fields = ['id', 'has_attending_note']
        
    def get_has_attending_note(self, obj):
        """
        Retourne True si le book_purchase associé a une note de remerciement
        """
        return bool(obj.book_purchase.attending_note if obj.book_purchase else False)
    
    def validate(self, data):
        book_purchase_id = data.get('book_purchase_id')

        if not book_purchase_id:
            raise serializers.ValidationError("Book Purchase ID is required.")

        try:
            book_purchase = BookPurchase.objects.get(id=book_purchase_id)
        except BookPurchase.DoesNotExist:
            raise serializers.ValidationError("Invalid Book Purchase ID")

        if data.get('guest_picture') and not book_purchase.allow_picture:
            raise serializers.ValidationError("Adding guest picture is not allowed for this book purchase.")

        if data.get('guest_name') and not book_purchase.allow_name:
            raise serializers.ValidationError("Adding guest name is not allowed for this book purchase.")

        if data.get('guest_address') and not book_purchase.allow_address:
            raise serializers.ValidationError("Adding guest address is not allowed for this book purchase.")

        if data.get('guest_email') and not book_purchase.allow_email:
            raise serializers.ValidationError("Adding guest email is not allowed for this book purchase.")

        if data.get('special_notes') and not book_purchase.allow_special_notes:
            raise serializers.ValidationError("Adding special notes is not allowed for this book purchase.")

        return data

    def create(self, validated_data):
        book_purchase_id = validated_data.pop('book_purchase_id')
        try:
            book_purchase = BookPurchase.objects.get(id=book_purchase_id)
        except BookPurchase.DoesNotExist:
            raise serializers.ValidationError("Invalid Book Purchase ID")
            
        guest_info = GuestInfo.objects.create(book_purchase=book_purchase, **validated_data)
        
        if book_purchase.attending_note and guest_info.guest_email:
            try:
                context = {
                    'guest_name': guest_info.guest_name or 'Guest',
                    'guest_address': guest_info.guest_address,
                    'guest_email': guest_info.guest_email,
                    'deceased_name': book_purchase.deceased_name,
                    'attending_note': book_purchase.attending_note,
                    'book_purchaser_name': (book_purchase.user.full_name or book_purchase.user.email)
                }
                
                context['attending_note'] = substitute_variables(context['attending_note'], context)
                
                send_thank_you_email(
                    guest_info.guest_email, 
                    "Thank you for your condolences", 
                    context, 
                    book_purchase,
                    guest_info
                )
            except Exception as e:
                print(f"Error sending thank you note: {e}")
        
        return guest_info


class EmailSerializer(serializers.Serializer):
    from_email = serializers.EmailField(required=True)
    emails_to = serializers.ListField(child=serializers.EmailField(), required=True)
    message = serializers.CharField(required=True)
    custom_field_25 = serializers.BooleanField(default=False)
    custom_field_50 = serializers.BooleanField(default=False)
    custom_field_25_value = serializers.CharField(required=False)
    custom_field_50_value = serializers.CharField(required=False)
    special_note = serializers.BooleanField(default=False)
    attachments = serializers.ListField(child=FullURLFileField(required=False), required=False)
    book_purchase_id = serializers.UUIDField(required=True)
    
    def validate_book_purchase_id(self, value):
        """
        Checks that the BookPurchase ID exists in the database.
        """
        if not BookPurchase.objects.filter(id=value).exists():
            raise serializers.ValidationError("Invalid book purchase ID.")
        return value

    def validate(self, data):
        if data.get('custom_field_25') and not data.get('custom_field_25_value'):
            raise serializers.ValidationError("custom_field_25_value is required if custom_field_25 is True.")
        if data.get('custom_field_50') and not data.get('custom_field_50_value'):
            raise serializers.ValidationError("custom_field_50_value is required if custom_field_50 is True.")
        return data

