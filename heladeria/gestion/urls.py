from django.urls import path
from . import views

urlpatterns = [
    
    path('', views.inicio, name='inicio'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'), 

    
    path('tienda/', views.producto_listado, name='producto_listado'),
    path('carrito/', views.ver_carrito, name='ver_carrito'),
    path('carrito/agregar/<int:producto_id>/', views.agregar_a_carrito, name='agregar_a_carrito'),
    path('carrito/quitar/<int:producto_id>/', views.quitar_de_carrito, name='quitar_de_carrito'),
    path('ordenar/', views.finalizar_orden, name='finalizar_orden'),
    path('historial/', views.historial_pedidos, name='historial_pedidos'),

    
    path('reporte/clientes/', views.reporte_clientes, name='reporte_clientes'),
    
    
    path('marketing/', views.marketing_dashboard, name='marketing_dashboard'),
    path('marketing/promocion/crear/', views.crear_promocion, name='crear_promocion'),
    
    
    path('marketing/promocion/<int:pk>/editar/', views.editar_promocion, name='editar_promocion'), 
]
