from django.contrib import admin

from .models import AlteracaoInventario


@admin.register(AlteracaoInventario)
class AlteracaoInventarioAdmin(admin.ModelAdmin):
    list_display = (
        "item",
        "acao",
        "campo_alterado",
        "valor_anterior",
        "valor_novo",
        "usuario",
        "data_hora",
    )
    list_filter = ("acao", "data_hora")
    search_fields = ("item__nome", "campo_alterado")
    readonly_fields = (
        "item",
        "acao",
        "campo_alterado",
        "valor_anterior",
        "valor_novo",
        "usuario",
        "data_hora",
    )

    def has_add_permission(self, request):
        return False
