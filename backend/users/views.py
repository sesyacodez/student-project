from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.utils import extend_schema

from .models import User
from .serializers import (
    UserProfileSerializer,
    UserSerializer,
    CustomTokenObtainPairSerializer,
)
from .permissions import IsAdminRole

@extend_schema(tags=['Auth'])
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

@extend_schema(tags=['Auth'])
class CustomTokenRefreshView(TokenRefreshView):
    pass


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get_queryset(self):
        current_user = self.request.user
        queryset = User.objects.select_related("branch")

        if current_user.is_superuser:
            return queryset

        if current_user.branch:
            return queryset.filter(branch=current_user.branch)

        return queryset.none()