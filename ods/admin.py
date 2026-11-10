from django.contrib import admin

from .models import (
    DadoPesquisaODS,
    IndicadorODS,
    MedicaoIndicador,
    ODS,
    ODSIndicador,
    VinculoInventarioIndicador,
)


class ODSIndicadorInline(admin.TabularInline):
    model = ODSIndicador
    extra = 1


class VinculoInventarioInline(admin.TabularInline):
    model = VinculoInventarioIndicador
    extra = 1


@admin.register(ODS)
class ODSAdmin(admin.ModelAdmin):
    list_display = ("numero", "nome")
    ordering = ("numero",)


@admin.register(IndicadorODS)
class IndicadorODSAdmin(admin.ModelAdmin):
    list_display = ("nome", "meta", "regra_calculo")
    list_filter = ("regra_calculo",)
    search_fields = ("nome",)
    inlines = [ODSIndicadorInline, VinculoInventarioInline]


@admin.register(DadoPesquisaODS)
class DadoPesquisaODSAdmin(admin.ModelAdmin):
    list_display = ("indicador", "data_referencia", "valor", "origem_pesquisa")
    list_filter = ("indicador", "data_referencia")


@admin.register(MedicaoIndicador)
class MedicaoIndicadorAdmin(admin.ModelAdmin):
    list_display = ("indicador", "periodo", "valor_calculado", "data_calculo")
    list_filter = ("indicador",)
