from django.contrib import admin
from django.contrib.auth import views as auth
from django.http import HttpResponse
from django.urls import path
from merifield_portal.urls import urlpatterns as portal_urls
urlpatterns = portal_urls + [
    path('accounts/login/', auth.LoginView.as_view(template_name='account/login.html'), name='account_login'),
    path('accounts/logout/', auth.LogoutView.as_view(), name='account_logout'),
    path('accounts/signup/', lambda request: HttpResponse('signup test placeholder'), name='account_signup'),
    path('accounts/password/reset/', lambda request: HttpResponse('reset test placeholder'), name='account_reset_password'),
    path('admin/', admin.site.urls),
]
