from django.contrib.auth.models import AbstractUser
from django.db import models


class Perfil(models.TextChoices):
    """Perfis de acesso do sistema (BDP13)."""

    ADMINISTRADOR = "administrador", "Administrador"
    OPERADOR = "operador", "Operador de dados"
    GESTOR = "gestor", "Gestor do OTO"


class Usuario(AbstractUser):
    """Usuário do OTO.

    Mapeia a entidade Usuario = {id_usuario, nome, email, perfil, ativo} do
    modelo lógico. Estende o usuário padrão do Django para reaproveitar
    autenticação, hashing de senha e sessão.
    """

    perfil = models.CharField(
        "Perfil",
        max_length=20,
        choices=Perfil.choices,
        default=Perfil.OPERADOR,
    )
    ativo = models.BooleanField("Ativo", default=True)

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"
        ordering = ["username"]

    def __str__(self):
        nome = self.get_full_name() or self.username
        return f"{nome} ({self.get_perfil_display()})"

    # --- Regras de permissão por perfil (BDP13) ---
    @property
    def eh_administrador(self) -> bool:
        return self.perfil == Perfil.ADMINISTRADOR or self.is_superuser

    @property
    def eh_operador(self) -> bool:
        return self.perfil == Perfil.OPERADOR or self.eh_administrador

    @property
    def eh_gestor(self) -> bool:
        return self.perfil == Perfil.GESTOR or self.eh_administrador

    def pode_gerenciar_usuarios(self) -> bool:
        """Apenas o administrador gerencia usuários e permissões."""
        return self.eh_administrador

    def pode_editar_inventario(self) -> bool:
        """Operador e administrador editam o Inventário Turístico."""
        return self.eh_operador

    def pode_consultar_indicadores(self) -> bool:
        """Gestor e administrador consultam indicadores ODS."""
        return self.eh_gestor

    def pode_importar(self) -> bool:
        """Importação do Inventário é feita pelo administrador."""
        return self.eh_administrador

    def save(self, *args, **kwargs):
        # Mantém is_active (controle real de login do Django) em sincronia
        # com o campo de negócio "ativo".
        self.is_active = self.ativo
        super().save(*args, **kwargs)
