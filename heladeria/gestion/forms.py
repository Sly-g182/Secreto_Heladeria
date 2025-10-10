from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.contrib.auth.models import User

from .models import Cliente, Promocion, Producto 



class ClienteUserCreationForm(UserCreationForm):


    
    rut = forms.CharField(max_length=15, required=False, label="RUT/Identificación")
    telefono = forms.CharField(max_length=20, required=False, label="Teléfono")
    direccion = forms.CharField(max_length=200, required=False, label="Dirección")
    
    
    first_name = forms.CharField(max_length=150, required=True, label="Nombre")
    last_name = forms.CharField(max_length=150, required=True, label="Apellido")
    email = forms.EmailField(required=True, label="Correo Electrónico")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('first_name', 'last_name', 'email', 'rut', 'telefono', 'direccion')
        
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este correo electrónico ya está registrado.")
        return email

    def save(self, commit=True):
    
        user = super().save(commit=False)
        user.email = self.cleaned_data['email'] 
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
            
            
            Cliente.objects.create(
                user=user, 
                rut=self.cleaned_data.get('rut'), 
                telefono=self.cleaned_data.get('telefono'),
                direccion=self.cleaned_data.get('direccion'),
            )
        
        return user



class PromocionForm(forms.ModelForm):

    """Formulario para crear y editar promociones."""
    
    productos = forms.ModelMultipleChoiceField(
        queryset=Producto.objects.all().order_by('nombre'),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Productos (dejar vacío para aplicar a TODA la tienda)"
    )

    class Meta:
        model = Promocion
        fields = ['nombre', 'descripcion', 'tipo', 'valor_descuento', 'fecha_inicio', 'fecha_fin', 'productos', 'activa']
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'type': 'date'}),
            'descripcion': forms.Textarea(attrs={'rows': 2}),
        }

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')
        valor_descuento = cleaned_data.get('valor_descuento')
        tipo = cleaned_data.get('tipo')

        if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
            self.add_error('fecha_fin', "La fecha de fin no puede ser anterior a la fecha de inicio.")

        if tipo in ['PORCENTAJE', 'VALOR_FIJO'] and valor_descuento is None:
            self.add_error('valor_descuento', "El valor de descuento es obligatorio para este tipo de promoción.")
        
        if tipo == 'PORCENTAJE' and (valor_descuento is not None and (valor_descuento < 1 or valor_descuento > 100)):
            self.add_error('valor_descuento', "El porcentaje debe estar entre 1 y 100.")

        return cleaned_data
        
        

class AgregarAlCarritoForm(forms.Form):

    """
    Formulario simple para añadir un producto al carrito.
    """
    cantidad = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-sm text-center', 
            'min': 1,
            'max': 99, 
        })
    )
    
    producto_id = forms.IntegerField(
        widget=forms.HiddenInput()
    )
    
    promocion_aplicada_id = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput()
    )
