from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import User
from .serializers import UserSerializer


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        current_user = self.request.user
        
        if current_user.is_superuser:
            return User.objects.all()
            
        if current_user.branch:
            return User.objects.filter(branch=current_user.branch)
            
        return User.objects.none()