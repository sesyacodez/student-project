from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import AuthenticationFailed
from rest_framework import serializers

from .models import User


class UserProfileSerializer(serializers.ModelSerializer):
    branches = serializers.SerializerMethodField()
    branch_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = ("id", "phone", "first_name", "last_name", "role", "branches", "branch_id")

    def get_branches(self, obj):
        return [obj.branch_id] if obj.branch_id else []

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        try:
            data = super().validate(attrs)
        except AuthenticationFailed:
            raise AuthenticationFailed("Wrong phone number or password.")
        
        if not self.user.is_active:
            raise AuthenticationFailed("This account is deactivated. Please contact the administrator.")

        user_payload = UserProfileSerializer(self.user).data
        data["user"] = user_payload
        data["id"] = user_payload.get("id")
        data["phone"] = user_payload.get("phone")
        data["first_name"] = user_payload.get("first_name")
        data["last_name"] = user_payload.get("last_name")
        data["role"] = user_payload.get("role")
        data["branches"] = user_payload.get("branches", [])
        data["branch_id"] = user_payload.get("branch_id")
        
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