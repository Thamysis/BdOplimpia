from django.urls import path

from . import views

app_name = "ods"

urlpatterns = [
    path("", views.IndicadorListView.as_view(), name="indicador_lista"),
    path("novo/", views.IndicadorCreateView.as_view(), name="indicador_novo"),
    path("<int:pk>/", views.IndicadorDetailView.as_view(), name="indicador_detalhe"),
    path(
        "<int:pk>/calcular/",
        views.CalcularMedicaoView.as_view(),
        name="calcular_medicao",
    ),
    path(
        "dados-pesquisa/novo/",
        views.DadoPesquisaCreateView.as_view(),
        name="dado_pesquisa_novo",
    ),
]
