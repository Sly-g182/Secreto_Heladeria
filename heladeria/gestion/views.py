from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction

from django.db.models import Sum, F, Max, Count
from datetime import date, timedelta 



from .models import Cliente, Producto, Promocion, Venta, DetalleVenta
from .forms import ClienteUserCreationForm, PromocionForm 





def is_staff_user(user):
    """Retorna True si el usuario es staff (Admin Marketing incluido)."""
    return user.is_staff

def is_cliente_user(user):
    """Retorna True si el usuario está autenticado y NO es staff."""
    return user.is_authenticated and not user.is_staff


def inicio(request):
    """Renderiza la página de inicio de Secreto Heladería y redirige a staff al dashboard."""
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('marketing_dashboard')
    
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
@user_passes_test(is_staff_user, login_url='/') 
def reporte_clientes(request):
    """Vista de reporte de todos los clientes (acceso para administración o marketing)."""
    
    datos_clientes = (
        Cliente.objects
        .select_related('user')
        .annotate(
            total_ordenes=Count('ventas__id', distinct=True),
            monto_total_gastado=Sum('ventas__total'),
            ultima_compra=Max('ventas__fecha_venta')
        )
        .order_by('-monto_total_gastado')
    )
    
    context = {'datos_clientes': datos_clientes}
    return render(request, 'gestion/reporte_clientes.html', context)



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
@user_passes_test(is_cliente_user, login_url='/admin/') 
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
            carrito[producto_id_str]['cantidad'] = nueva_cantidad
        else:
            carrito[producto_id_str] = {
                'id': producto.id,
                'nombre': producto.nombre,
                'precio': str(producto.precio),
                'cantidad': cantidad,
            }

        request.session['carrito'] = carrito
        request.session.modified = True
        messages.success(request, f"{producto.nombre} añadido al pedido.")

    return redirect('producto_listado')


@login_required
@user_passes_test(is_cliente_user, login_url='/admin/') 
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
@user_passes_test(is_cliente_user, login_url='/admin/') 
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
@user_passes_test(is_cliente_user, login_url='/admin/') 
def finalizar_orden(request):
    """Crea una venta y sus detalles a partir del carrito."""
    carrito = request.session.get('carrito', {})

    if not carrito:
        messages.error(request, "El carrito está vacío. Añade productos para ordenar.")
        return redirect('producto_listado')

    try:
        with transaction.atomic():
            
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

                
                promociones = Promocion.objects.filter(
                    productos=producto,
                    fecha_inicio__lte=hoy,
                    fecha_fin__gte=hoy,
                    tipo='PORCENTAJE' 
                )

                precio_a_usar = precio_unitario_base
                
                if promociones.exists():
                    
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
@user_passes_test(is_cliente_user, login_url='/admin/') 
def historial_pedidos(request):
    """Muestra el historial de compras del cliente."""
    try:
        cliente = get_object_or_404(Cliente, user=request.user)
        
        pedidos = Venta.objects.filter(cliente=cliente).prefetch_related('detalles__producto').order_by('-fecha_venta')

        context = {'pedidos': pedidos}
        return render(request, 'productos/historial_pedidos.html', context)

    except Cliente.DoesNotExist:
        messages.error(request, "No se encontró tu perfil de cliente. ¿Iniciaste sesión?")
        return redirect('producto_listado')




@login_required
@user_passes_test(is_staff_user, login_url='/') 
def marketing_dashboard(request):
    """Vista para el administrador de marketing, ahora incluye analíticas y todas las promociones."""
    hoy = date.today()
    fecha_limite_vencimiento = hoy + timedelta(days=30)
    
    
    resumen = {
        'total_clientes': Cliente.objects.count(),
        
        'total_ventas': Venta.objects.count(), 
        'total_productos': Producto.objects.count(),
        'promociones_activas': Promocion.objects.filter(fecha_fin__gte=hoy).count(),
        'ventas_total_monto': Venta.objects.aggregate(total=Sum('total'))['total'] or 0,
    }

    
    ultimas_ventas = (
        Venta.objects
        .select_related('cliente__user')
        .prefetch_related('detalles__producto')
        .order_by('-fecha_venta')[:5]
    )
    
    
    productos_mas_vendidos = (
        DetalleVenta.objects
        .values('producto__nombre')
        .annotate(total_vendido=Sum('cantidad'))
        .order_by('-total_vendido')[:5]
    )

    
    productos_por_vencer = Producto.objects.filter(
        fecha_vencimiento__lte=fecha_limite_vencimiento,
        fecha_vencimiento__gte=hoy,
        stock__gt=0
    ).order_by('fecha_vencimiento')

    
    todas_promociones = Promocion.objects.all().order_by('-fecha_inicio')

    context = {
        'resumen': resumen,
        'ultimas_ventas': ultimas_ventas,
        'productos_mas_vendidos': productos_mas_vendidos,
        'productos_por_vencer': productos_por_vencer,
        'todas_promociones': todas_promociones,
    }

    return render(request, 'gestion/marketing_dashboard.html', context)


@login_required
@user_passes_test(is_staff_user, login_url='/') 
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

    
    productos = Producto.objects.all() 
    context = {'form': form, 'productos': productos, 'modo': 'Crear'}
    return render(request, 'gestion/crear_promocion.html', context)


@login_required
@user_passes_test(is_staff_user, login_url='/') 
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

    return render(request, 'gestion/crear_promocion.html', context)


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect('inicio')
