from django.contrib import admin

from .models import (
    Cadastur,
    CampoSegmento,
    Cnae,
    Contato,
    ItemInventario,
    Participa,
    Preenchimento,
    ProfissionalTurismo,
    Segmento,
)


class ParticipaInline(admin.TabularInline):
    model = Participa
    extra = 1


class PreenchimentoInline(admin.TabularInline):
    model = Preenchimento
    extra = 0


class CampoSegmentoInline(admin.TabularInline):
    model = CampoSegmento
    extra = 1


@admin.register(Segmento)
class SegmentoAdmin(admin.ModelAdmin):
    list_display = ("nome", "descricao")
    search_fields = ("nome",)
    inlines = [CampoSegmentoInline]


@admin.register(ItemInventario)
class ItemInventarioAdmin(admin.ModelAdmin):
    list_display = ("nome", "bairro", "status", "documento", "atualizado_em")
    list_filter = ("status", "participa__segmento")
    search_fields = ("nome", "razao_social", "documento")
    inlines = [ParticipaInline, PreenchimentoInline]


@admin.register(Cnae)
class CnaeAdmin(admin.ModelAdmin):
    list_display = ("codigo", "descricao")
    search_fields = ("codigo", "descricao")


@admin.register(ProfissionalTurismo)
class ProfissionalTurismoAdmin(admin.ModelAdmin):
    list_display = ("nome", "cpf", "classificacao")
    search_fields = ("nome", "cpf")


admin.site.register(Contato)
admin.site.register(Cadastur)
admin.site.register(CampoSegmento)
admin.site.register(Preenchimento)
admin.site.site_header = "OTO — Base de Dados Principal"
admin.site.site_title = "OTO"
admin.site.index_title = "Administração"
