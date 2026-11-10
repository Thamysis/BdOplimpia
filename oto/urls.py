from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import include, path


def health(request):
    return JsonResponse({"status": "ok"})


@login_required
def painel(request):
    """Painel inicial com atalhos conforme o perfil do usuário."""
    from importacao.models import Importacao
    from inventario.models import ItemInventario, StatusItem
    from ods.models import IndicadorODS

    contexto = {
        "total_ativos": ItemInventario.objects.filter(status=StatusItem.ATIVO).count(),
        "total_inativos": ItemInventario.objects.filter(
            status=StatusItem.INATIVO
        ).count(),
        "total_indicadores": IndicadorODS.objects.count(),
        "ultimas_importacoes": Importacao.objects.all()[:5],
    }
    return render(request, "painel.html", contexto)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
    path("", painel, name="painel"),
    path("acesso/", include("acesso.urls")),
    path("inventario/", include("inventario.urls")),
    path("importacao/", include("importacao.urls")),
    path("ods/", include("ods.urls")),
]
