# heladeria/gestion/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from datetime import date

# Modelos y formularios
from .models import Cliente, Producto, Promocion, Venta, DetalleVenta
from .forms import ClienteUserCreationForm


# ------------------------------------------------------------------------
# VISTAS DE AUTENTICACIÓN Y DASHBOARD PRINCIPAL
# ------------------------------------------------------------------------

def inicio(request):
    """Renderiza la página de inicio de Secreto Heladería."""
    return render(request, 'gestion/inicio.html')


def register(request):
    """Maneja el registro de nuevos clientes."""
    if request.method == 'POST':
        form = ClienteUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "¡Registro exitoso! Ya puedes empezar a ordenar.")
            return redirect('producto_listado')
    else:
        form = ClienteUserCreationForm()
    
    return render(request, 'gestion/register.html', {'form': form})


@login_required
def reporte_clientes(request):
    """Vista de reporte de todos los clientes (acceso para administración o marketing)."""
    clientes = Cliente.objects.all()
    return render(request, 'gestion/reporte_clientes.html', {'clientes': clientes})


# ------------------------------------------------------------------------
# VISTAS DE CLIENTE (TIENDA)
# ------------------------------------------------------------------------

def producto_listado(request):
    """Muestra todos los productos en stock, agrupados por categoría y con promociones activas."""
    hoy = date.today()
    productos_en_stock = Producto.objects.filter(stock__gt=0).select_related('categoria')

    promociones_activas = Promocion.objects.filter(
        fecha_inicio__lte=hoy,
        fecha_fin__gte=hoy
    ).prefetch_related('productos')
    
    promociones_por_producto = {}
    for promo in promociones_activas:
        for producto in promo.productos.all():
            if producto.id in [p.id for p in productos_en_stock]:
                if producto.id not in promociones_por_producto:
                    promociones_por_producto[producto.id] = []
                promociones_por_producto[producto.id].append({
                    'nombre': promo.nombre,
                    'descuento': promo.descuento
                })

    categorias = {}
    for producto in productos_en_stock:
        cat_nombre = producto.categoria.nombre
        if cat_nombre not in categorias:
            categorias[cat_nombre] = []
        categorias[cat_nombre].append(producto)

    context = {
        'categorias': categorias.items(),
        'promociones_por_producto': promociones_por_producto,
    }

    return render(request, 'productos/listado.html', context)


@login_required
def agregar_a_carrito(request, producto_id):
    """Agrega productos al carrito almacenado en sesión."""
    if request.method == 'POST':
        producto = get_object_or_404(Producto, id=producto_id)
        try:
            cantidad = int(request.POST.get('cantidad', 1))
            if cantidad <= 0:
                raise ValueError
        except ValueError:
            messages.error(request, "La cantidad debe ser un número positivo.")
            return redirect('producto_listado')
        
        carrito = request.session.get('carrito', {})
        producto_id_str = str(producto_id)

        if producto_id_str in carrito:
            nueva_cantidad = carrito[producto_id_str]['cantidad'] + cantidad
            carrito[producto_id_str]['cantidad'] = min(nueva_cantidad, producto.stock)
        else:
            carrito[producto_id_str] = {
                'id': producto.id,
                'nombre': producto.nombre,
                'precio': str(producto.precio),
                'cantidad': min(cantidad, producto.stock),
            }

        request.session['carrito'] = carrito
        request.session.modified = True
        messages.success(request, f"{producto.nombre} añadido al pedido.")

    return redirect('producto_listado')


@login_required
def ver_carrito(request):
    """Muestra el contenido actual del carrito."""
    carrito = request.session.get('carrito', {})
    productos_en_carrito = []
    total_general = 0

    for id_str, item in list(carrito.items()):
        try:
            producto = Producto.objects.get(id=int(id_str))
            precio_unitario = float(item['precio'])
            subtotal = precio_unitario * item['cantidad']

            productos_en_carrito.append({
                'id': producto.id,
                'nombre': producto.nombre,
                'cantidad': item['cantidad'],
                'precio_unitario': precio_unitario,
                'subtotal': subtotal
            })
            total_general += subtotal
        except Producto.DoesNotExist:
            del carrito[id_str]
            request.session.modified = True

    if request.session.modified:
        request.session['carrito'] = carrito

    context = {
        'productos': productos_en_carrito,
        'total_general': total_general
    }

    return render(request, 'productos/carrito.html', context)


@login_required
def quitar_de_carrito(request, producto_id):
    """Quita un producto del carrito."""
    carrito = request.session.get('carrito', {})
    producto_id_str = str(producto_id)

    if producto_id_str in carrito:
        del carrito[producto_id_str]
        messages.info(request, "Producto eliminado del pedido.")

        request.session['carrito'] = carrito
        request.session.modified = True

    return redirect('ver_carrito')


@login_required
def finalizar_orden(request):
    """Crea una venta y sus detalles a partir del carrito."""
    carrito = request.session.get('carrito', {})

    if not carrito:
        messages.error(request, "El carrito está vacío. Añade productos para ordenar.")
        return redirect('producto_listado')

    try:
        with transaction.atomic():
            cliente = get_object_or_404(Cliente, correo=request.user.email)

            venta = Venta.objects.create(cliente=cliente)
            total_venta = 0
            hoy = date.today()

            for id_str, item in carrito.items():
                producto = get_object_or_404(Producto, id=int(id_str))
                cantidad = item['cantidad']
                precio_unitario_base = producto.precio

                if producto.stock < cantidad:
                    raise Exception(f"Stock insuficiente para {producto.nombre}. Disponible: {producto.stock}")

                promociones = Promocion.objects.filter(
                    productos=producto,
                    fecha_inicio__lte=hoy,
                    fecha_fin__gte=hoy
                )

                precio_a_usar = precio_unitario_base
                if promociones.exists():
                    max_descuento = max(p.descuento for p in promociones)
                    precio_a_usar = precio_unitario_base * (1 - (max_descuento / 100))

                subtotal = precio_a_usar * cantidad
                total_venta += subtotal

                DetalleVenta.objects.create(
                    venta=venta,
                    producto=producto,
                    cantidad=cantidad,
                    precio_unitario=precio_a_usar,
                    subtotal=subtotal
                )

            venta.total = total_venta
            venta.save()

            del request.session['carrito']
            request.session.modified = True

            messages.success(request, f"¡Tu pedido #{venta.id} ha sido completado con éxito! Revisa tu historial.")
            return redirect('historial_pedidos')

    except Exception as e:
        messages.error(request, f"Error al procesar el pedido: {str(e)}. No se ha cobrado nada.")
        return redirect('ver_carrito')


@login_required
def historial_pedidos(request):
    """Muestra el historial de compras del cliente."""
    try:
        cliente = get_object_or_404(Cliente, correo=request.user.email)
        pedidos = Venta.objects.filter(cliente=cliente).prefetch_related('detalles__producto').order_by('-fecha_venta')

        context = {'pedidos': pedidos}
        return render(request, 'productos/historial_pedidos.html', context)

    except Cliente.DoesNotExist:
        messages.error(request, "No se encontró tu perfil de cliente. ¿Iniciaste sesión?")
        return redirect('producto_listado')


# ------------------------------------------------------------------------
# DASHBOARD DE MARKETING
# ------------------------------------------------------------------------

@login_required
def marketing_dashboard(request):
    """Vista para el administrador de marketing."""
    resumen = {
        'total_clientes': Cliente.objects.count(),
        'total_ventas': Venta.objects.count(),
        'total_productos': Producto.objects.count(),
        'promociones_activas': Promocion.objects.filter(fecha_fin__gte=date.today()).count(),
    }

    ultimas_ventas = (
        Venta.objects
        .select_related('cliente')
        .prefetch_related('detalles__producto')
        .order_by('-fecha_venta')[:5]
    )

    context = {
        'resumen': resumen,
        'ultimas_ventas': ultimas_ventas,
    }

    return render(request, 'gestion/marketing_dashboard.html', context)

# ------------------------------------------------------------------------
# CREAR PROMOCIÓN (ADMINISTRADOR DE MARKETING)
# ------------------------------------------------------------------------

@login_required
def crear_promocion(request):
    """Permite al administrador de marketing crear nuevas promociones."""
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion')
        descuento = request.POST.get('descuento')
        fecha_inicio = request.POST.get('fecha_inicio')
        fecha_fin = request.POST.get('fecha_fin')
        productos_ids = request.POST.getlist('productos')  # IDs de productos seleccionados

        if not (nombre and descuento and fecha_inicio and fecha_fin):
            messages.error(request, "Todos los campos obligatorios deben completarse.")
            return redirect('crear_promocion')

        try:
            descuento = float(descuento)
            if descuento <= 0 or descuento > 100:
                raise ValueError
        except ValueError:
            messages.error(request, "El descuento debe ser un número válido entre 1 y 100.")
            return redirect('crear_promocion')

        promocion = Promocion.objects.create(
            nombre=nombre,
            descripcion=descripcion,
            descuento=descuento,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        promocion.productos.set(productos_ids)
        promocion.save()

        messages.success(request, f"Promoción '{nombre}' creada exitosamente.")
        return redirect('marketing_dashboard')

    productos = Producto.objects.all()
    context = {'productos': productos}
    return render(request, 'gestion/crear_promocion.html', context)
