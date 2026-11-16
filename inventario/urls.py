from django.urls import path

from . import views

app_name = "inventario"

urlpatterns = [
    path("", views.ItemListView.as_view(), name="lista"),
    path("relatorios/", views.RelatoriosView.as_view(), name="relatorios"),
    path("catalogos/", views.CatalogosView.as_view(), name="catalogos"),
    path("catalogos/segmentos/novo/", views.SegmentoCreateView.as_view(), name="segmento_novo"),
    path("catalogos/campos/novo/", views.CampoSegmentoCreateView.as_view(), name="campo_novo"),
    path("catalogos/cnaes/novo/", views.CnaeCreateView.as_view(), name="cnae_novo"),
    path("catalogos/profissionais/novo/", views.ProfissionalCreateView.as_view(), name="profissional_novo"),
    path("novo/", views.ItemCreateView.as_view(), name="novo"),
    path("<int:pk>/", views.ItemDetailView.as_view(), name="detalhe"),
    path("<int:pk>/editar/", views.ItemUpdateView.as_view(), name="editar"),
    path("<int:pk>/dados/", views.DadosComplementaresView.as_view(), name="dados_complementares"),
    path("<int:pk>/inativar/", views.ItemInativarView.as_view(), name="inativar"),
    path("<int:pk>/reativar/", views.ItemReativarView.as_view(), name="reativar"),
]
