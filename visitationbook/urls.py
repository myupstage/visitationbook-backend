"""
URL configuration for visitationbook project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
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
from django.conf.urls.static import static
from django.urls import path, re_path, include
from django.shortcuts import redirect
from visitationbookapi.routers import router
from visitationbookapi.viewsets import *
from visitationbookapi.views import *
from visitationbook import settings

from rest_framework import permissions
from rest_framework_simplejwt.views import (TokenRefreshView, TokenVerifyView)
from drf_yasg.views import get_schema_view

from dj_rest_auth.registration.views import (
    SocialAccountListView, SocialAccountDisconnectView
)

schema_view = get_schema_view(
    settings.api_info,
    # url=settings.API_URL, 
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('', redirect_to_swagger, name='home'),
    path('admin/', admin.site.urls),
    
    # Swagger/OpenAPI documentation
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    re_path(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    re_path(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    # API URLs
    path('api/', include(router.urls)),
    path('api/password_reset/', include('django_rest_passwordreset.urls', namespace='password_reset')),
    path('api/change_password/', ChangePasswordView.as_view(), name='change_password'),
    path('api/register/', RegisterView.as_view(), name='register'),
    path('api/login/', LoginView.as_view(), name='login'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('api/auth/me/', UserDetailView.as_view(), name='user_detail'),
    
    # AllAuth URLs (nécessaire pour l'authentification sociale)
    path('accounts/', include('allauth.urls')),
    
    # Authentication URLs
    path('api/auth/', include('dj_rest_auth.urls')),
    path('api/auth/registration/', include('dj_rest_auth.registration.urls')),
    path('api/auth/social/google/', GoogleLoginView.as_view(), name='google_login'),
    path('api/auth/social/facebook/', FacebookLoginView.as_view(), name='fb_login'),
    
    # Social account management
    path('api/socialaccounts/', SocialAccountListView.as_view(), name='social_account_list'),
    path('api/socialaccounts/<int:pk>/disconnect/', SocialAccountDisconnectView.as_view(), name='social_account_disconnect'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
