from django.db import models

class Cliente(models.Model):
    nombre = models.CharField(max_length=100)
    rut = models.CharField(max_length=12, unique=True)
    telefono = models.CharField(max_length=15)
    correo = models.EmailField()
    direccion = models.CharField(max_length=150)
    fecha_registro = models.DateField(auto_now_add=True)
    ultima_compra = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.nombre
