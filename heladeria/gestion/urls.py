from django.urls import path
from . import views

urlpatterns = [
    path('', views.reporte_clientes, name='inicio'),  # 👈 ahora la raíz muestra el reporte
    path('reporte-clientes/', views.reporte_clientes, name='reporte_clientes'),
]


