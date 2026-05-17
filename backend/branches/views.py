from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Branch
from .serializers import BranchSerializer
from users.permissions import IsAdminRole

class BranchViewSet(viewsets.ModelViewSet):
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    permission_classes = [IsAdminRole] 

def get_queryset(self):
        current_user = self.request.user
        if current_user.is_superuser:
            return Branch.objects.all()
        if current_user.branch:
            return Branch.objects.filter(id=current_user.branch.id)
        return Branch.objects.none()