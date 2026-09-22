from rest_framework import serializers
from .models import CustomUser, DriverProfile, EmergencyContact


class EmergencyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = [
            'id',
            'name',
            'phone',
            'relation',
            'can_receive_sms',
            'can_receive_call',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class TrustScoreBreakdownSerializer(serializers.Serializer):
    ratings_avg = serializers.FloatField()
    safe_trips_pct = serializers.FloatField()
    account_age_pct = serializers.FloatField()
    verified_pct = serializers.FloatField()
    weights = serializers.DictField()
    ratings_count = serializers.IntegerField()
    verified = serializers.BooleanField()
    account_days = serializers.IntegerField()
    incident_free_trips = serializers.IntegerField()


class TrustScoreSerializer(serializers.Serializer):
    trust_score = serializers.FloatField()
    level = serializers.CharField()
    breakdown = TrustScoreBreakdownSerializer()


class DriverProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverProfile
        fields = [
            'id',
            'phone_number',
            'license_number',
            'vehicle_type',
            'plate_number',
            'license_photo',
            'vehicle_photo',
            'cni_photo',
            'profile_photo',
            'birth_date',
            'verified',
            'is_active',
            'documents',
            'qr_code',
            'face_embedding',
        ]
        read_only_fields = ['id', 'verified', 'qr_code', 'face_embedding']


class UserSerializer(serializers.ModelSerializer):
    phone = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()
    trust_score = serializers.SerializerMethodField()
    is_verified = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    driver_profile = DriverProfileSerializer(read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            'id',
            'phone',
            'first_name',
            'last_name',
            'photo_url',
            'email',
            'role',
            'trust_score',
            'is_verified',
            'is_active',
            'created_at',
            'driver_profile',
        ]
        read_only_fields = [
            'id',
            'phone',
            'photo_url',
            'role',
            'trust_score',
            'is_verified',
            'is_active',
            'created_at',
            'driver_profile',
        ]

    def get_phone(self, obj):
        return obj.username

    def get_photo_url(self, obj):
        return None

    def get_trust_score(self, obj):
        try:
            from ratings.utils import calculate_trust_score
            return float(calculate_trust_score(obj).get('trust_score', 5.0))
        except Exception:
            return 5.0

    def get_is_verified(self, obj):
        profile = getattr(obj, 'driver_profile', None)
        return bool(getattr(profile, 'verified', False))

    def get_created_at(self, obj):
        return obj.date_joined.isoformat()


class RegisterSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(required=False, allow_blank=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ['username', 'phone', 'email', 'first_name', 'last_name', 'password', 'role']
        extra_kwargs = {
            'username': {'required': False, 'allow_blank': True},
        }

    def create(self, validated_data):
        password = validated_data.pop('password')
        phone = validated_data.pop('phone', '').strip()
        username = validated_data.pop('username', '').strip()

        if phone:
            validated_data['username'] = phone
        elif username:
            validated_data['username'] = username
        else:
            raise serializers.ValidationError({'phone': 'Phone or username is required.'})

        user = CustomUser(**validated_data)
        user.set_password(password)
        user.save()
        if user.role == 'driver':
            DriverProfile.objects.create(user=user)
        return user
