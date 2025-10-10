from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.db.models import F 
from django.contrib.auth.models import User 
from django.core.exceptions import ValidationError 



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
    
    
    def clean(self):
        """Asegura que el stock no sea un valor negativo."""
        if self.stock < 0:
            raise ValidationError({'stock': "El stock de un producto no puede ser un valor negativo."})
        
        
        super().clean()

    @property
    def esta_por_vencer(self):
        """Retorna True si el producto vence en menos de 7 días"""
        if self.fecha_vencimiento:
            return (self.fecha_vencimiento - timezone.now().date()) <= timedelta(days=7)
        return False


class Promocion(models.Model):
    
    TIPO_CHOICES = [
        ('PORCENTAJE', 'Porcentaje (%)'),
        ('VALOR_FIJO', 'Valor Fijo ($)'),
        ('2X1', '2x1 (Llevar 2, Pagar 1)'), 
    ]
    
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    
    
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, help_text="Tipo de descuento aplicado.")
    
    
    valor_descuento = models.DecimalField(
        max_digits=10, decimal_places=2, 
        blank=True, null=True, 
        help_text="El valor del descuento (ej: 10 para 10% o 5000 para $5000)"
    )
    
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    productos = models.ManyToManyField(Producto, blank=True, related_name="promociones")
    
    
    activa = models.BooleanField(default=True, help_text="Marcar para que la promoción esté disponible.")

    def __str__(self):
        return self.nombre
    
    
    def clean(self):
        """Asegura que la fecha de inicio no sea posterior a la fecha de fin."""
        if self.fecha_inicio and self.fecha_fin and self.fecha_inicio > self.fecha_fin:
            raise ValidationError({
                'fecha_inicio': "La fecha de inicio no puede ser posterior a la fecha de fin de la promoción."
            })
        super().clean()


    @property
    def es_vigente(self):
        """Devuelve True si la promoción está activa y dentro del rango de fechas"""
        hoy = timezone.now().date()
        return self.activa and (self.fecha_inicio <= hoy <= self.fecha_fin)




class Cliente(models.Model):
    """
    Representa el perfil extendido del cliente y se vincula 1:1 con el usuario de Django (User).
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True) 
    
    telefono = models.CharField(max_length=20, blank=True, null=True)
    direccion = models.CharField(max_length=200, blank=True, null=True)
    rut = models.CharField(max_length=15, blank=True, null=True) 

    @property
    def correo(self):
        """Acceso al email del usuario de Django."""
        return self.user.email 
    
    @property
    def nombre(self):
        """Acceso al nombre y apellido del usuario de Django."""
        if self.user.first_name and self.user.last_name:
            return f"{self.user.first_name} {self.user.last_name}"
        return self.user.username

    def __str__(self):
        return self.nombre




class Venta(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, related_name="ventas") 
    fecha_venta = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Venta #{self.id} - {self.cliente.nombre if self.cliente else 'Cliente Eliminado'}"

    def calcular_total(self):
        """Recalcula el total de la venta sumando los subtotales de todos sus detalles."""
        from django.db.models import Sum
        suma = self.detalles.aggregate(total_suma=Sum('subtotal'))['total_suma']
        self.total = suma if suma is not None else 0.00
        self.save()


class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name="detalles")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT) 
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, editable=False) 
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, editable=False)

    class Meta:
        verbose_name = "Detalle de Venta"
        verbose_name_plural = "Detalles de Venta"
        
    def __str__(self):
        return f"{self.producto.nombre} x {self.cantidad} en Venta #{self.venta.id}"

    def save(self, *args, **kwargs):
        """
        Calcula subtotal, guarda el precio unitario, actualiza el stock con F-expressions
        y recalcula el total de la Venta.
        """
        
        if not self.pk: 

            if not self.precio_unitario:
                    self.precio_unitario = self.producto.precio
        
        self.subtotal = self.precio_unitario * self.cantidad
        
        super().save(*args, **kwargs)
        
        Producto.objects.filter(pk=self.producto_id).update(stock=F('stock') - self.cantidad)
        
        self.venta.calcular_total()
