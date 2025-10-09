# heladeria/gestion/context_processors.py (CORREGIDO)

def roles(request):
    """Añade booleanos de chequeo de rol al contexto de la plantilla."""
    
    # 🚨 Accedemos al usuario directamente desde el request
    user = request.user
    
    # Funciones que verifican el rol (ya no necesitan argumentos)
    def es_admin():
        # Verificamos si el usuario está autenticado antes de chequear grupos
        if not user.is_authenticated:
            return False
        return user.is_superuser or user.groups.filter(name='Administradores').exists()

    def es_mktg_o_admin():
        if not user.is_authenticated:
            return False
        return user.is_superuser or user.groups.filter(name__in=['Administradores', 'Marketing']).exists()

    return {
        # 🚨 Exportamos las funciones SIN paréntesis para usarlas en el IF
        'es_admin_role': es_admin,
        'es_mktg_o_admin_role': es_mktg_o_admin,
    }