from django.urls import path

from . import views

app_name = "ods"

urlpatterns = [
    path("", views.IndicadorListView.as_view(), name="indicador_lista"),
    path("novo/", views.IndicadorCreateView.as_view(), name="indicador_novo"),
    path("objetivos/novo/", views.ODSCreateView.as_view(), name="objetivo_novo"),
    path("<int:pk>/editar/", views.IndicadorUpdateView.as_view(), name="indicador_editar"),
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
