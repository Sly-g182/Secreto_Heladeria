from django.contrib import admin
from .models import Categoria, Producto, Cliente, Promocion, Venta, DetalleVenta
from datetime import date, timedelta


# --- Inline para mostrar los detalles dentro de una venta ---
class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 0
    readonly_fields = ('producto', 'cantidad', 'subtotal')


# --- Modelo Venta ---
@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'fecha_venta', 'total')
    list_filter = ('fecha_venta',)
    search_fields = ('cliente__nombre',)
    date_hierarchy = 'fecha_venta'
    inlines = [DetalleVentaInline]


# --- Modelo Producto ---
@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'precio', 'stock', 'fecha_vencimiento', 'esta_por_vencer')
    list_filter = ('categoria',)
    search_fields = ('nombre',)
    readonly_fields = ('esta_por_vencer',)

    # Acción personalizada: marcar productos por vencer para promoción
    actions = ['mostrar_productos_por_vencer']

    @admin.action(description="Mostrar productos que vencen en menos de 7 días")
    def mostrar_productos_por_vencer(self, request, queryset):
        por_vencer = queryset.filter(fecha_vencimiento__lte=date.today() + timedelta(days=7))
        count = por_vencer.count()
        self.message_user(request, f"{count} producto(s) están por vencer.")
        return por_vencer


# --- Modelo Categoria ---
@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre',)


# --- Modelo Cliente ---
@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'correo', 'telefono')
    search_fields = ('nombre', 'correo')


# --- Modelo Promocion ---
@admin.register(Promocion)
class PromocionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descuento', 'fecha_inicio', 'fecha_fin', 'activa')
    filter_horizontal = ('productos',)
    list_filter = ('fecha_inicio', 'fecha_fin')
    search_fields = ('nombre',)


# --- Modelo DetalleVenta (opcional, ya se ve como inline) ---
@admin.register(DetalleVenta)
class DetalleVentaAdmin(admin.ModelAdmin):
    list_display = ('venta', 'producto', 'cantidad', 'subtotal')
    search_fields = ('venta__id', 'producto__nombre')
