"""Auditoria do Inventário (RN03 / RF15).

Registra cada alteração em itens do inventário: usuário responsável, data/hora,
ação, campo alterado e valores anterior e novo.
"""
from django.conf import settings
from django.db import models

from inventario.models import ItemInventario


class AcaoAuditoria(models.TextChoices):
    CRIACAO = "criacao", "Criação"
    EDICAO = "edicao", "Edição"
    INATIVACAO = "inativacao", "Inativação"
    REATIVACAO = "reativacao", "Reativação"


class AlteracaoInventario(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="alteracoes",
        verbose_name="Usuário responsável",
    )
    item = models.ForeignKey(
        ItemInventario,
        on_delete=models.CASCADE,
        related_name="historico",
        verbose_name="Item",
    )
    data_hora = models.DateTimeField("Data/hora", auto_now_add=True)
    acao = models.CharField("Ação", max_length=20, choices=AcaoAuditoria.choices)
    campo_alterado = models.CharField("Campo alterado", max_length=120, blank=True)
    valor_anterior = models.TextField("Valor anterior", blank=True)
    valor_novo = models.TextField("Valor novo", blank=True)

    class Meta:
        verbose_name = "Alteração do Inventário"
        verbose_name_plural = "Alterações do Inventário"
        ordering = ["-data_hora", "-id"]

    def __str__(self):
        return f"{self.get_acao_display()} em {self.item} ({self.data_hora:%d/%m/%Y %H:%M})"
