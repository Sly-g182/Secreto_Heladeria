# heladeria/urls.py

from django.contrib import admin
from django.urls import path, include
# Importa las vistas de autenticación de Django
from django.contrib.auth import views as auth_views 

urlpatterns = [
    # 1. Rutas de administración
    path('admin/', admin.site.urls),
    
    # 2. RUTA DE INICIO DE SESIÓN (Ajuste para usar tu plantilla)
    # Sobrescribimos la vista de login para que use la plantilla 'gestion/login.html'
    path('login/', auth_views.LoginView.as_view(template_name='gestion/login.html'), name='login'),
    
    # 3. Resto de Rutas de Autenticación de Django (logout, password_reset, etc.)
    # Nota: Ponemos el include *después* de nuestra definición de 'login'
    path('', include('django.contrib.auth.urls')), 
    
    # 4. Rutas de tu aplicación 'gestion'
    path('', include('gestion.urls')),
]