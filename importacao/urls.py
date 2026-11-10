from django.urls import path

from . import views

app_name = "importacao"

urlpatterns = [
    path("", views.ImportacaoView.as_view(), name="importar"),
    path("oficial/", views.ImportacaoOficialView.as_view(), name="importar_oficial"),
    path("confirmar/", views.ImportacaoConfirmarView.as_view(), name="confirmar"),
    path("cancelar/", views.ImportacaoCancelarView.as_view(), name="cancelar"),
    path("historico/", views.ImportacaoListView.as_view(), name="historico"),
    path("<int:pk>/", views.ImportacaoDetailView.as_view(), name="detalhe"),
]
