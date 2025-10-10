from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.core.exceptions import ValidationError
from .models import Categoria, Producto, Promocion, Cliente, Venta, DetalleVenta

# =================================================================
# INLINE DE PRODUCTOS PARA PROMOCION
# =================================================================
class ProductoInline(admin.TabularInline):
    model = Promocion.productos.through  # tabla intermedia many-to-many
    extra = 1
    verbose_name = "Producto en promoción"
    verbose_name_plural = "Productos en promoción"

# =================================================================
# ACCIÓN PERSONALIZADA
# =================================================================
def activar_promociones(modeladmin, request, queryset):
    updated = queryset.update(activa=True)
    modeladmin.message_user(request, f"{updated} promoción(es) activada(s).")
activar_promociones.short_description = "Activar promociones seleccionadas"

# =================================================================
# ADMIN DE PROMOCION
# =================================================================
@admin.register(Promocion)
class PromocionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'valor_descuento', 'rango_fechas', 'es_vigente_status', 'num_productos')
    list_filter = ('activa', 'tipo', 'fecha_inicio', 'fecha_fin')
    search_fields = ('nombre', 'descripcion')
    date_hierarchy = 'fecha_inicio'
    filter_horizontal = ('productos',)
    inlines = [ProductoInline]
    actions = [activar_promociones]

    def rango_fechas(self, obj):
        return f"{obj.fecha_inicio.strftime('%d/%m/%y')} a {obj.fecha_fin.strftime('%d/%m/%y')}"
    rango_fechas.short_description = "Vigencia"

    def es_vigente_status(self, obj):
        if obj.es_vigente:
            return format_html('<span style="color: green; font-weight: bold;">ACTIVA</span>')
        elif obj.fecha_fin < timezone.now().date():
            return format_html('<span style="color: red;">FINALIZADA</span>')
        elif not obj.activa:
            return format_html('<span style="color: orange;">INACTIVA (Manual)</span>')
        else:
            return format_html('<span style="color: blue;">PRÓXIMA</span>')
    es_vigente_status.short_description = 'Estado'

    def num_productos(self, obj):
        return obj.productos.count() if obj.productos.exists() else "Global/Todos"
    num_productos.short_description = 'Aplica a'

    def save_model(self, request, obj, form, change):
        if obj.fecha_fin < obj.fecha_inicio:
            raise ValidationError("La fecha fin no puede ser anterior a la fecha inicio.")
        super().save_model(request, obj, form, change)

    # ===========================
    # Permisos correctos para superuser y Marketing
    # ===========================
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if request.user.groups.filter(name='Marketing').exists():
            return qs
        return qs.none()

    def has_add_permission(self, request):
        return request.user.is_superuser or request.user.groups.filter(name='Marketing').exists()

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.groups.filter(name='Marketing').exists()

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.groups.filter(name='Marketing').exists()


# =================================================================
# MODELOS GENERALES
# =================================================================
@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'precio', 'stock', 'fecha_vencimiento_format', 'es_por_vencer')
    list_filter = ('categoria', 'stock')
    search_fields = ('nombre', 'descripcion')
    date_hierarchy = 'fecha_vencimiento'
    ordering = ('categoria__nombre', 'nombre')
    list_editable = ('precio', 'stock')

    def fecha_vencimiento_format(self, obj):
        return obj.fecha_vencimiento.strftime('%d/%m/%Y') if obj.fecha_vencimiento else "-"
    fecha_vencimiento_format.short_description = "Vencimiento"

    def es_por_vencer(self, obj):
        if obj.esta_por_vencer:
             return format_html('<span style="color: red; font-weight: bold;">¡PRONTO!</span>')
        return format_html('<span style="color: green;">OK</span>')
    es_por_vencer.short_description = 'Alerta Vencimiento'

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


# =================================================================
# INLINE DETALLE VENTA
# =================================================================
class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 1  # permite añadir nuevas filas
    readonly_fields = ('subtotal', 'precio_unitario')
    # editable fields: producto y cantidad
    fields = ('producto', 'cantidad', 'precio_unitario', 'subtotal')


# =================================================================
# ADMIN VENTA CON INLINE
# =================================================================
@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente_nombre', 'fecha_venta', 'total_formateado')
    list_filter = ('fecha_venta',)
    search_fields = ('cliente__user__username', 'id')
    inlines = [DetalleVentaInline]
    readonly_fields = ('total', 'fecha_venta')

    def cliente_nombre(self, obj):
        return obj.cliente.nombre if obj.cliente else "N/A"
    cliente_nombre.short_description = 'Cliente'
    
    def total_formateado(self, obj):
        return f"${obj.total:,.2f}"
    total_formateado.short_description = 'Total Venta'
