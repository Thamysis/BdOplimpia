from django.urls import path

from . import views

app_name = "acesso"

urlpatterns = [
    path("login/", views.LoginOTOView.as_view(), name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("usuarios/", views.UsuarioListView.as_view(), name="usuario_lista"),
    path("usuarios/novo/", views.UsuarioCreateView.as_view(), name="usuario_novo"),
    path(
        "usuarios/<int:pk>/editar/",
        views.UsuarioUpdateView.as_view(),
        name="usuario_editar",
    ),
]
