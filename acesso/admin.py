from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ("username", "first_name", "last_name", "email", "perfil", "ativo")
    list_filter = ("perfil", "ativo", "is_staff")
    fieldsets = UserAdmin.fieldsets + (
        ("Perfil OTO", {"fields": ("perfil", "ativo")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Perfil OTO", {"fields": ("perfil", "ativo")}),
    )
