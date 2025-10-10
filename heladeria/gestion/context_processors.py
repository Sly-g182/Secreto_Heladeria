

def roles(request):
    """Añade booleanos de chequeo de rol al contexto de la plantilla."""
    
    
    user = request.user
    
    
    def es_admin():
        
        if not user.is_authenticated:
            return False
        return user.is_superuser or user.groups.filter(name='Administradores').exists()

    def es_mktg_o_admin():
        if not user.is_authenticated:
            return False
        return user.is_superuser or user.groups.filter(name__in=['Administradores', 'Marketing']).exists()

    return {
        
        'es_admin_role': es_admin,
        'es_mktg_o_admin_role': es_mktg_o_admin,
    }