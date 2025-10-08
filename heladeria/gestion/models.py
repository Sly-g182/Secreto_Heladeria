from django.db import models
from django.utils import timezone
from datetime import timedelta


class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    fecha_vencimiento = models.DateField(blank=True, null=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name="productos")

    def __str__(self):
        return self.nombre

    @property
    def esta_por_vencer(self):
        """Retorna True si el producto vence en menos de 7 días"""
        if self.fecha_vencimiento:
            return (self.fecha_vencimiento - timezone.now().date()) <= timedelta(days=7)
        return False


class Cliente(models.Model):
    nombre = models.CharField(max_length=100)
    correo = models.EmailField(unique=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    direccion = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return self.nombre


class Promocion(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    descuento = models.DecimalField(max_digits=5, decimal_places=2, help_text="Porcentaje de descuento (ej: 10.00)")
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    productos = models.ManyToManyField(Producto, blank=True, related_name="promociones")

    def __str__(self):
        return self.nombre

    @property
    def activa(self):
        """Devuelve True si la promoción está vigente"""
        hoy = timezone.now().date()
        return self.fecha_inicio <= hoy <= self.fecha_fin


class Venta(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="ventas")
    fecha_venta = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Venta #{self.id} - {self.cliente.nombre}"

    def calcular_total(self):
        total = sum(detalle.subtotal for detalle in self.detalles.all())
        self.total = total
        self.save()


class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name="detalles")
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.producto.nombre} x {self.cantidad}"

    def save(self, *args, **kwargs):
        """Calcula subtotal automático"""
        self.subtotal = self.producto.precio * self.cantidad
        super().save(*args, **kwargs)
        # Actualiza stock del producto
        self.producto.stock -= self.cantidad
        self.producto.save()
        # Recalcula total de la venta
        self.venta.calcular_total()
