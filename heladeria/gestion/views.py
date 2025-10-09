from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
# Importaciones necesarias para cálculos
from django.db.models import Sum, F, Max, Count
from datetime import date, timedelta 


# Modelos y formularios
from .models import Cliente, Producto, Promocion, Venta, DetalleVenta
from .forms import ClienteUserCreationForm, PromocionForm 


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
    
    datos_clientes = (
        Cliente.objects
        .select_related('user')
        .annotate(
            # Total de órdenes: cuenta los IDs de venta distintos a través de la relación 'ventas'
            total_ordenes=Count('ventas__id', distinct=True),
            # Monto total gastado: suma el campo 'total' de todas las ventas a través de la relación 'ventas'
            monto_total_gastado=Sum('ventas__total'),
            # Última compra: encuentra la fecha_venta máxima a través de la relación 'ventas'
            ultima_compra=Max('ventas__fecha_venta')
        )
        # ELIMINADO: La línea .filter(total_ordenes__gt=0) se eliminó para mostrar
        # a TODOS los clientes, incluidos los recién registrados sin pedidos.
        .order_by('-monto_total_gastado')
    )
    
    context = {'datos_clientes': datos_clientes}
    return render(request, 'gestion/reporte_clientes.html', context)


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
        productos_aplicables = promo.productos.all()
        
        if not productos_aplicables:
            productos_a_iterar = productos_en_stock
        else:
            # Filtramos productos en stock que están específicamente en esta promoción
            productos_a_iterar = productos_en_stock.filter(id__in=[p.id for p in productos_aplicables])

        for producto in productos_a_iterar:
            if producto.id not in promociones_por_producto:
                promociones_por_producto[producto.id] = []
            
            promociones_por_producto[producto.id].append({
                'nombre': promo.nombre,
                'descuento': promo.valor_descuento, 
                'tipo': promo.tipo
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
            # Si el producto ya no existe en la base de datos, lo quitamos del carrito
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
            # Asumo que el modelo Cliente se relaciona con User. 
            cliente = get_object_or_404(Cliente, user=request.user) 

            venta = Venta.objects.create(cliente=cliente)
            total_venta = 0
            hoy = date.today()

            for id_str, item in carrito.items():
                producto = get_object_or_404(Producto, id=int(id_str))
                cantidad = item['cantidad']
                precio_unitario_base = producto.precio

                if producto.stock < cantidad:
                    raise Exception(f"Stock insuficiente para {producto.nombre}. Disponible: {producto.stock}")

                # Lógica para aplicar la mejor promoción (solo aplica descuento si es PORCENTAJE)
                promociones = Promocion.objects.filter(
                    productos=producto,
                    fecha_inicio__lte=hoy,
                    fecha_fin__gte=hoy,
                    tipo='PORCENTAJE' 
                )

                precio_a_usar = precio_unitario_base
                
                if promociones.exists():
                    # Encuentra el máximo descuento porcentual
                    max_descuento_porcentaje = max(p.valor_descuento for p in promociones) 
                    precio_a_usar = precio_unitario_base * (1 - (max_descuento_porcentaje / 100))

                subtotal = precio_a_usar * cantidad
                total_venta += subtotal

                DetalleVenta.objects.create(
                    venta=venta,
                    producto=producto,
                    cantidad=cantidad,
                    precio_unitario=precio_a_usar,
                    subtotal=subtotal
                )
                
                # Actualizar stock (IMPORTANTE)
                producto.stock -= cantidad
                producto.save()


            venta.total = total_venta
            venta.save()

            del request.session['carrito']
            request.session.modified = True

            messages.success(request, f"¡Tu pedido #{venta.id} ha sido completado con éxito! Revisa tu historial.")
            return redirect('historial_pedidos')

    except Cliente.DoesNotExist:
        messages.error(request, "No se encontró tu perfil de cliente. Asegúrate de que tu perfil exista.")
        return redirect('producto_listado')
    except Exception as e:
        messages.error(request, f"Error al procesar el pedido: {str(e)}. No se ha cobrado nada.")
        return redirect('ver_carrito')


@login_required
def historial_pedidos(request):
    """Muestra el historial de compras del cliente."""
    try:
        cliente = get_object_or_404(Cliente, user=request.user)
        # prefetch_related es crucial para evitar múltiples consultas a la base de datos
        pedidos = Venta.objects.filter(cliente=cliente).prefetch_related('detalles__producto').order_by('-fecha_venta')

        context = {'pedidos': pedidos}
        return render(request, 'productos/historial_pedidos.html', context)

    except Cliente.DoesNotExist:
        messages.error(request, "No se encontró tu perfil de cliente. ¿Iniciaste sesión?")
        return redirect('producto_listado')


# ------------------------------------------------------------------------
# DASHBOARD DE MARKETING Y VISTAS DE PROMOCIÓN
# ------------------------------------------------------------------------

@login_required
def marketing_dashboard(request):
    """Vista para el administrador de marketing, ahora incluye analíticas y todas las promociones."""
    hoy = date.today()
    fecha_limite_vencimiento = hoy + timedelta(days=30)
    
    # 1. Resumen general
    resumen = {
        'total_clientes': Cliente.objects.count(),
        'total_ventas': Venta.objects.count(),
        'total_productos': Producto.objects.count(),
        'promociones_activas': Promocion.objects.filter(fecha_fin__gte=hoy).count(),
        'ventas_total_monto': Venta.objects.aggregate(total=Sum('total'))['total'] or 0,
    }

    # 2. Últimas compras (para historial)
    ultimas_ventas = (
        Venta.objects
        .select_related('cliente__user') # Accedemos al usuario a través del cliente
        .prefetch_related('detalles__producto')
        .order_by('-fecha_venta')[:5]
    )
    
    # 3. Productos más vendidos (Top 5)
    productos_mas_vendidos = (
        DetalleVenta.objects
        .values('producto__nombre') # Agrupar por nombre de producto
        .annotate(total_vendido=Sum('cantidad')) # Sumar la cantidad vendida
        .order_by('-total_vendido')[:5]
    )

    # 4. Productos por vencer (en los próximos 30 días)
    productos_por_vencer = Producto.objects.filter(
        fecha_vencimiento__lte=fecha_limite_vencimiento,
        fecha_vencimiento__gte=hoy, # Solo los que vencen a partir de hoy
        stock__gt=0 # Solo si tienen stock
    ).order_by('fecha_vencimiento')

    # 5. TODAS las promociones (para listado y edición)
    todas_promociones = Promocion.objects.all().order_by('-fecha_inicio')

    context = {
        'resumen': resumen,
        'ultimas_ventas': ultimas_ventas,
        'productos_mas_vendidos': productos_mas_vendidos,
        'productos_por_vencer': productos_por_vencer,
        'todas_promociones': todas_promociones, # Se añade el listado completo
    }

    return render(request, 'gestion/marketing_dashboard.html', context)


@login_required
def crear_promocion(request):
    """Permite al administrador de marketing crear nuevas promociones usando el PromocionForm."""
    
    if request.method == 'POST':
        form = PromocionForm(request.POST) 
        
        if form.is_valid():
            promocion = form.save() 
            messages.success(request, f"Promoción '{promocion.nombre}' creada exitosamente.")
            return redirect('marketing_dashboard')
        else:
            messages.error(request, "Error al crear la promoción. Revisa los campos marcados y la fecha.")
    else:
        form = PromocionForm() 

    # Rendeza la plantilla con el formulario (vacío o con errores)
    productos = Producto.objects.all() 
    context = {'form': form, 'productos': productos, 'modo': 'Crear'}
    return render(request, 'gestion/crear_promocion.html', context)


@login_required
def editar_promocion(request, pk):
    """Permite al administrador de marketing editar una promoción existente."""
    promocion = get_object_or_404(Promocion, pk=pk)

    if request.method == 'POST':
        form = PromocionForm(request.POST, instance=promocion)
        if form.is_valid():
            form.save()
            messages.success(request, f"Promoción '{promocion.nombre}' actualizada exitosamente.")
            return redirect('marketing_dashboard')
        else:
            messages.error(request, "Error al actualizar la promoción. Revisa los campos marcados.")
    else:
        form = PromocionForm(instance=promocion)

    productos = Producto.objects.all()
    context = {'form': form, 'productos': productos, 'promocion': promocion, 'modo': 'Editar'}
    # Se reutiliza la plantilla de creación para la edición
    return render(request, 'gestion/crear_promocion.html', context)


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect('inicio')
