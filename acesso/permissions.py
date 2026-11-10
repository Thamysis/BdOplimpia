"""Mixins de controle de acesso por perfil (BDP13).

Centraliza a verificação de permissão para ser reutilizada pelas views das
demais apps. Usuário não autenticado é redirecionado ao login; autenticado sem
permissão recebe 403.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class PerfilRequiredMixin(LoginRequiredMixin):
    #: nome do método de verificação em ``Usuario`` (ex.: "pode_editar_inventario")
    verificacao = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        if self.verificacao is not None:
            checar = getattr(request.user, self.verificacao)
            if not checar():
                raise PermissionDenied(
                    "Seu perfil não tem permissão para esta ação."
                )
        return super().dispatch(request, *args, **kwargs)


class GerenciaUsuariosRequiredMixin(PerfilRequiredMixin):
    verificacao = "pode_gerenciar_usuarios"


class EditaInventarioRequiredMixin(PerfilRequiredMixin):
    verificacao = "pode_editar_inventario"


class ImportaRequiredMixin(PerfilRequiredMixin):
    verificacao = "pode_importar"


class ConsultaIndicadoresRequiredMixin(PerfilRequiredMixin):
    verificacao = "pode_consultar_indicadores"
