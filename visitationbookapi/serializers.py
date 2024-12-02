from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from visitationbookapi.models import *
from visitationbookapi.utils import *
import datetime


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


class UserSerializer(serializers.ModelSerializer):
    payment_methods = serializers.SerializerMethodField()
    payment_transactions = serializers.SerializerMethodField()
    book_purchases = serializers.SerializerMethodField()
    obituaries = serializers.SerializerMethodField()
    profile_image = FullURLFileField()
    
    class Meta:
        model = User
        extra_kwargs = {
            'password': {'write_only': True, 'required': False}
        }
        fields = ('id', 'email', 'full_name', 'address', 'security_question', 'security_answer', 
                  'name_funeral_home', 'phone', 'password', 'profile_image', 'original_file_name', 'content_type',
                  'payment_methods', 'payment_transactions', 'book_purchases', 'obituaries', 'stripe_customer_id')
        
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

    class Meta:
        model = BookPurchase
        fields = ['id', 'book_id', 'book', 'obituary_id', 'obituary', 'custom_cover', 'custom_text_color', 'payment_status', 'purchase_date',
                  'payment_transaction', 'deceased_image', 'deceased_name', 'date_of_birth', 'date_of_death', 
                  'allow_picture', 'allow_name', 'allow_address', 'allow_email', 'allow_special_notes',
                  'guests', 'is_both', 'pdf_file', 'is_complete', 'visit_count']
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
        
        if not book_id:
            raise serializers.ValidationError("Book ID is required for creating a book purchase.")
        
        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            raise serializers.ValidationError("Invalid book ID")
        
        book_purchase = BookPurchase.objects.create(book=book, **validated_data)
        
        if obituary_id:
            try:
                obituary = Obituary.objects.get(id=obituary_id)
                book_purchase.obituary = obituary
                book_purchase.save()
            except Obituary.DoesNotExist:
                raise serializers.ValidationError("Invalid obituary ID")
            
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

    class Meta:
        model = BookPurchase
        fields = ['id', 'book', 'obituary', 'custom_cover', 'custom_text_color', 'deceased_name', 'date_of_birth', 'date_of_death', 'deceased_image',
                  'allow_picture', 'allow_name', 'allow_address', 'allow_email', 'allow_special_notes', 'guests', 'pdf_file', 'is_complete']

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
    
    class Meta:
        model = GuestInfo
        fields = ['id', 'book_purchase_id', 'guest_picture', 'guest_name', 'guest_address', 'guest_email', 'special_notes']
    
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

