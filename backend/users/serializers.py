from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import AuthenticationFailed
from rest_framework import serializers
from .models import User

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        try:
            data = super().validate(attrs)
        except AuthenticationFailed:
            raise AuthenticationFailed("Wrong phone number or password.")
        
        if not self.user.is_active:
            raise AuthenticationFailed("This account is deactivated. Please contact the administrator.")

        data['role'] = self.user.role
        data['first_name'] = self.user.first_name
        data['branch_id'] = self.user.branch.id if self.user.branch else None
        
        return data
    
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'phone', 'first_name', 'last_name', 'role', 'branch', 'is_active', 'password')
        extra_kwargs = {
            'password': {'write_only': True} 
        }

    def create(self, validated_data):
        user = User(**validated_data)
        user.set_password(validated_data['password'])
        user.save()
        return user