from django.urls import path

from . import views

app_name = "inventario"

urlpatterns = [
    path("", views.ItemListView.as_view(), name="lista"),
    path("relatorios/", views.RelatoriosView.as_view(), name="relatorios"),
    path("novo/", views.ItemCreateView.as_view(), name="novo"),
    path("<int:pk>/", views.ItemDetailView.as_view(), name="detalhe"),
    path("<int:pk>/editar/", views.ItemUpdateView.as_view(), name="editar"),
    path("<int:pk>/inativar/", views.ItemInativarView.as_view(), name="inativar"),
    path("<int:pk>/reativar/", views.ItemReativarView.as_view(), name="reativar"),
]
