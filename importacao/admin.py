from django.contrib import admin

from .models import FonteDados, Importacao, InconsistenciaImportacao


class InconsistenciaInline(admin.TabularInline):
    model = InconsistenciaImportacao
    extra = 0
    readonly_fields = ("referencia_origem", "tipo", "descricao", "status")
    can_delete = False


@admin.register(FonteDados)
class FonteDadosAdmin(admin.ModelAdmin):
    list_display = ("nome", "tipo", "formato")
    search_fields = ("nome",)


@admin.register(Importacao)
class ImportacaoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "arquivo_origem",
        "status",
        "qtd_registros",
        "qtd_importados",
        "qtd_rejeitados",
        "usuario",
        "data_hora",
    )
    list_filter = ("status", "data_hora")
    inlines = [InconsistenciaInline]
    readonly_fields = ("data_hora",)
