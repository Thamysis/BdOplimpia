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


# Equipe de desenvolvimento, curso e instituição exibidos na página de créditos.
EQUIPE = [
    ("Caio Delgado Pires", "caiopires@usp.br"),
    (
        "Estefano Rafael Malaquias Alves Nascimento",
        "estefano.nascimento@usp.br",
    ),
    ("Pyerry Klyzlow Xavier", "xavier.pyerry@usp.br"),
    ("Thamyres Santos Silva", "thamyres.santos.silva@usp.br"),
    ("Enzo Vasconcellos Pagotto", "enzopagotto@usp.br"),
]
CURSO = "Bacharelado em Sistemas de Informação"
INSTITUICAO = "USP — ICMC (Instituto de Ciências Matemáticas e de Computação)"
ANO_DESENVOLVIMENTO = 2026


@login_required
def creditos(request):
    """Créditos do projeto: equipe, curso, instituição e ano."""
    contexto = {
        "equipe": [{"nome": nome, "email": email} for nome, email in EQUIPE],
        "curso": CURSO,
        "instituicao": INSTITUICAO,
        "ano": ANO_DESENVOLVIMENTO,
    }
    return render(request, "creditos.html", contexto)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
    path("", painel, name="painel"),
    path("creditos/", creditos, name="creditos"),
    path("acesso/", include("acesso.urls")),
    path("inventario/", include("inventario.urls")),
    path("importacao/", include("importacao.urls")),
    path("ods/", include("ods.urls")),
]
