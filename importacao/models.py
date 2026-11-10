"""Importação do Inventário e registro de inconsistências (BDP01 / BDP11)."""
from django.conf import settings
from django.db import models


class FonteDados(models.Model):
    nome = models.CharField("Nome", max_length=120)
    tipo = models.CharField("Tipo", max_length=60, blank=True)
    formato = models.CharField("Formato", max_length=20, blank=True)

    class Meta:
        verbose_name = "Fonte de dados"
        verbose_name_plural = "Fontes de dados"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class StatusImportacao(models.TextChoices):
    PENDENTE = "pendente", "Pendente"
    VALIDADA = "validada", "Validada"
    CONCLUIDA = "concluida", "Concluída"
    COM_INCONSISTENCIAS = "com_inconsistencias", "Com inconsistências"


class Importacao(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="importacoes",
        verbose_name="Responsável",
    )
    fonte = models.ForeignKey(
        FonteDados,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="importacoes",
        verbose_name="Fonte",
    )
    data_hora = models.DateTimeField("Data/hora", auto_now_add=True)
    arquivo_origem = models.CharField("Arquivo de origem", max_length=255, blank=True)
    status = models.CharField(
        "Status",
        max_length=25,
        choices=StatusImportacao.choices,
        default=StatusImportacao.PENDENTE,
    )
    qtd_registros = models.PositiveIntegerField("Registros lidos", default=0)
    qtd_importados = models.PositiveIntegerField("Registros importados", default=0)
    qtd_rejeitados = models.PositiveIntegerField("Registros rejeitados", default=0)

    class Meta:
        verbose_name = "Importação"
        verbose_name_plural = "Importações"
        ordering = ["-data_hora", "-id"]

    def __str__(self):
        return f"Importação #{self.pk} - {self.arquivo_origem or 'sem arquivo'}"


class TipoInconsistencia(models.TextChoices):
    DUPLICIDADE = "duplicidade", "Duplicidade"
    CAMPO_OBRIGATORIO = "campo_obrigatorio", "Campo obrigatório ausente"
    FORMATO = "formato", "Formato inválido"


class InconsistenciaImportacao(models.Model):
    importacao = models.ForeignKey(
        Importacao,
        on_delete=models.CASCADE,
        related_name="inconsistencias",
        verbose_name="Importação",
    )
    referencia_origem = models.CharField(
        "Referência de origem", max_length=120,
        help_text="Linha ou identificador na origem.",
    )
    tipo = models.CharField("Tipo", max_length=25, choices=TipoInconsistencia.choices)
    descricao = models.CharField("Descrição/Motivo", max_length=255)
    status = models.CharField("Status", max_length=40, default="pendente")

    class Meta:
        verbose_name = "Inconsistência de importação"
        verbose_name_plural = "Inconsistências de importação"
        ordering = ["importacao", "referencia_origem"]

    def __str__(self):
        return f"{self.get_tipo_display()} ({self.referencia_origem})"
