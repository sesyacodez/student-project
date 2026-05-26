"""
URL configuration for edumanage project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from users.views import CurrentUserView, CustomTokenObtainPairView, CustomTokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/login/', CustomTokenObtainPairView.as_view(), name='auth-login'),
    path('api/v1/auth/refresh/', CustomTokenRefreshView.as_view(), name='auth-refresh'),
    path('api/v1/auth/me/', CurrentUserView.as_view(), name='auth-me'),
    path('api/v1/', include('branches.urls')),
    path('api/v1/', include('students_and_groups.urls')),
    path('api/v1/', include('subscriptions.urls')),
    path('api/v1/', include('scheduling.urls')),
    path('api/v1/users/', include('users.urls')),
    path('api/v1/branches/', include('branches.urls')),

    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
