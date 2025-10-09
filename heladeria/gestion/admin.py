from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
# Importa todos los modelos para registrarlos
from .models import Categoria, Producto, Promocion, Cliente, Venta, DetalleVenta 

# =================================================================
# PROMOCION ADMIN
# =================================================================

@admin.register(Promocion)
class PromocionAdmin(admin.ModelAdmin):
    # ¡LISTA DE PANTALLA CORREGIDA! Usamos 'tipo', 'valor_descuento' y los campos personalizados.
    list_display = ('nombre', 'tipo', 'valor_descuento', 'rango_fechas', 'es_vigente_status', 'num_productos')
    list_filter = ('activa', 'tipo', 'fecha_inicio', 'fecha_fin')
    search_fields = ('nombre', 'descripcion')
    date_hierarchy = 'fecha_inicio'
    filter_horizontal = ('productos',) # Mejora la interfaz para seleccionar productos
    
    # Campo personalizado para mostrar las fechas
    def rango_fechas(self, obj):
        return f"{obj.fecha_inicio.strftime('%d/%m/%y')} a {obj.fecha_fin.strftime('%d/%m/%y')}"
    rango_fechas.short_description = "Vigencia"

    # Campo personalizado para mostrar si es vigente con colores
    def es_vigente_status(self, obj):
        # Utilizamos la propiedad 'es_vigente' que definimos en models.py
        if obj.es_vigente:
            return format_html('<span style="color: green; font-weight: bold;">ACTIVA</span>')
        elif obj.fecha_fin < timezone.now().date():
            return format_html('<span style="color: red;">FINALIZADA</span>')
        elif not obj.activa:
            return format_html('<span style="color: orange;">INACTIVA (Manual)</span>')
        else:
            return format_html('<span style="color: blue;">PRÓXIMA</span>')

    es_vigente_status.boolean = False
    es_vigente_status.short_description = 'Estado'

    # Contador de productos relacionados
    def num_productos(self, obj):
        # Retorna el conteo de productos a los que aplica
        return obj.productos.count() if obj.productos.exists() else "Global/Todos"
    num_productos.short_description = 'Aplica a'


# =================================================================
# PRODUCTO ADMIN
# =================================================================

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'precio', 'stock', 'fecha_vencimiento_format', 'es_por_vencer')
    list_filter = ('categoria', 'stock')
    search_fields = ('nombre', 'descripcion')
    date_hierarchy = 'fecha_vencimiento'
    ordering = ('categoria__nombre', 'nombre')
    list_editable = ('precio', 'stock') # Permite editar precio y stock desde la lista

    def fecha_vencimiento_format(self, obj):
        return obj.fecha_vencimiento.strftime('%d/%m/%Y') if obj.fecha_vencimiento else "-"
    fecha_vencimiento_format.short_description = "Vencimiento"

    # Indicador de alerta de vencimiento
    def es_por_vencer(self, obj):
        if obj.esta_por_vencer:
             return format_html('<span style="color: red; font-weight: bold;">¡PRONTO!</span>')
        return format_html('<span style="color: green;">OK</span>')
    es_por_vencer.short_description = 'Alerta Vencimiento'
    es_por_vencer.boolean = False


# =================================================================
# CATEGORIA, CLIENTE, VENTA, DETALLE VENTA ADMIN
# =================================================================

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre',)

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('user', 'rut', 'telefono', 'direccion', 'num_ventas')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'rut')
    raw_id_fields = ('user',)

    def num_ventas(self, obj):
        return obj.ventas.count()
    num_ventas.short_description = 'N° Ventas'


class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 0
    # No se puede editar un detalle de venta histórico
    readonly_fields = ('producto', 'cantidad', 'precio_unitario', 'subtotal')
    can_delete = False

@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente_nombre', 'fecha_venta', 'total_formateado')
    list_filter = ('fecha_venta',)
    search_fields = ('cliente__user__username', 'id')
    inlines = [DetalleVentaInline]
    # No se permite cambiar el cliente, el total ni la fecha de una venta finalizada
    readonly_fields = ('cliente', 'total', 'fecha_venta')

    def cliente_nombre(self, obj):
        return obj.cliente.nombre if obj.cliente else "N/A"
    cliente_nombre.short_description = 'Cliente'
    
    def total_formateado(self, obj):
        return f"${obj.total:,.2f}" # Formato de moneda
    total_formateado.short_description = 'Total Venta'
