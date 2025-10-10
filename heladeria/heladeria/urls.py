

from django.contrib import admin
from django.urls import path, include

from django.contrib.auth import views as auth_views 

urlpatterns = [
    
    path('admin/', admin.site.urls),
    
    
    path('login/', auth_views.LoginView.as_view(template_name='gestion/login.html'), name='login'),
    
    
    path('', include('django.contrib.auth.urls')), 
    
    
    path('', include('gestion.urls')),
]