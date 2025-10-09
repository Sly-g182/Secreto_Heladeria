# heladeria/gestion/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # URLs de Autenticación
    path('', views.inicio, name='inicio'),
    path('register/', views.register, name='register'),
    # Asume que tienes un path para login/logout en tu urls.py principal o usando allauth
    
    # URLs de Gestión (Admin/Marketing)
    path('admin/clientes/', views.reporte_clientes, name='reporte_clientes'),
    path('marketing/dashboard/', views.marketing_dashboard, name='marketing_dashboard'),
    path('marketing/promocion/crear/', views.crear_promocion, name='crear_promocion'), # <-- Nuevo path
    
    # URLs de Cliente (Tienda y Carrito)
    path('productos/', views.producto_listado, name='producto_listado'),
    path('carrito/', views.ver_carrito, name='ver_carrito'),
    path('carrito/add/<int:producto_id>/', views.agregar_a_carrito, name='agregar_a_carrito'),
    path('carrito/remove/<int:producto_id>/', views.quitar_de_carrito, name='quitar_de_carrito'),
    path('ordenar/finalizar/', views.finalizar_orden, name='finalizar_orden'),
    path('pedidos/historial/', views.historial_pedidos, name='historial_pedidos'),
]