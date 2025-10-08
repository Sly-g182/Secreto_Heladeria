from django.shortcuts import render
from .models import Cliente

def reporte_clientes(request):
    clientes = Cliente.objects.all()
    return render(request, 'gestion/reporte_clientes.html', {'clientes': clientes})

