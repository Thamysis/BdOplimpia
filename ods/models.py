"""Módulo ODS — complementar (BDP08, BDP09, BDP10, BDP12).

Indicadores dos Objetivos de Desenvolvimento Sustentável, dados de pesquisa que
os alimentam, vínculo com o Inventário por regra de cálculo documentada e série
histórica de medições.
"""
from django.db import models

from inventario.models import ItemInventario


class ODS(models.Model):
    """Objetivo de Desenvolvimento Sustentável."""

    numero = models.PositiveSmallIntegerField("Número", null=True, blank=True)
    nome = models.CharField("Nome", max_length=255)

    class Meta:
        verbose_name = "ODS"
        verbose_name_plural = "ODS"
        ordering = ["numero", "nome"]

    def __str__(self):
        return f"ODS {self.numero} - {self.nome}" if self.numero else self.nome


class RegraCalculo(models.TextChoices):
    MANUAL = "manual", "Manual (dados de pesquisa)"
    CONTAR_ITENS_CAMPO = (
        "contar_itens_campo",
        "Contar itens ativos com campo = valor",
    )


class IndicadorODS(models.Model):
    nome = models.CharField("Nome", max_length=255)
    descricao = models.TextField("Descrição", blank=True)
    meta = models.CharField("Meta", max_length=255, blank=True)
    ods = models.ManyToManyField(
        ODS, through="ODSIndicador", related_name="indicadores", verbose_name="ODS"
    )

    # Regra de cálculo documentada (BDP10).
    regra_calculo = models.CharField(
        "Regra de cálculo",
        max_length=30,
        choices=RegraCalculo.choices,
        default=RegraCalculo.MANUAL,
    )
    regra_campo = models.CharField(
        "Campo da regra", max_length=120, blank=True,
        help_text="Nome do campo de segmento usado na regra automática.",
    )
    regra_valor = models.CharField(
        "Valor esperado da regra", max_length=120, blank=True,
        help_text="Valor que o campo deve ter para o item ser contado.",
    )
    regra_descricao = models.TextField("Descrição da regra", blank=True)

    class Meta:
        verbose_name = "Indicador ODS"
        verbose_name_plural = "Indicadores ODS"
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    def calcular(self) -> float:
        """Calcula a medição conforme a regra documentada (BDP10)."""
        from inventario.models import Preenchimento, StatusItem

        if self.regra_calculo == RegraCalculo.CONTAR_ITENS_CAMPO:
            qs = Preenchimento.objects.filter(
                campo__nome=self.regra_campo,
                valor=self.regra_valor,
                item__status=StatusItem.ATIVO,
            )
            return float(qs.values("item").distinct().count())
        # Regra manual: soma dos valores dos dados de pesquisa.
        total = self.dados_pesquisa.aggregate(s=models.Sum("valor"))["s"]
        return float(total or 0)


class ODSIndicador(models.Model):
    ods = models.ForeignKey(ODS, on_delete=models.CASCADE)
    indicador = models.ForeignKey(IndicadorODS, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Vínculo ODS-Indicador"
        verbose_name_plural = "Vínculos ODS-Indicador"
        constraints = [
            models.UniqueConstraint(
                fields=["ods", "indicador"], name="ods_indicador_unico"
            )
        ]


class VinculoInventarioIndicador(models.Model):
    """Relaciona itens do Inventário a um indicador (BDP10)."""

    indicador = models.ForeignKey(
        IndicadorODS,
        on_delete=models.CASCADE,
        related_name="itens_vinculados",
        verbose_name="Indicador",
    )
    item = models.ForeignKey(
        ItemInventario,
        on_delete=models.CASCADE,
        related_name="indicadores_vinculados",
        verbose_name="Item",
    )

    class Meta:
        verbose_name = "Vínculo Inventário-Indicador"
        verbose_name_plural = "Vínculos Inventário-Indicador"
        constraints = [
            models.UniqueConstraint(
                fields=["indicador", "item"], name="vinculo_inventario_indicador_unico"
            )
        ]


class DadoPesquisaODS(models.Model):
    """Dado de pesquisa que alimenta um indicador (BDP09)."""

    indicador = models.ForeignKey(
        IndicadorODS,
        on_delete=models.CASCADE,
        related_name="dados_pesquisa",
        verbose_name="Indicador",
    )
    origem_pesquisa = models.CharField("Origem da pesquisa", max_length=255, blank=True)
    data_referencia = models.DateField("Data de referência")
    valor = models.DecimalField("Valor", max_digits=15, decimal_places=4)
    observacao = models.TextField("Observação", blank=True)

    class Meta:
        verbose_name = "Dado de pesquisa ODS"
        verbose_name_plural = "Dados de pesquisa ODS"
        ordering = ["indicador", "data_referencia"]

    def __str__(self):
        return f"{self.indicador} ({self.data_referencia})"


class MedicaoIndicador(models.Model):
    """Medição calculada de um indicador em um período (BDP12)."""

    indicador = models.ForeignKey(
        IndicadorODS,
        on_delete=models.CASCADE,
        related_name="medicoes",
        verbose_name="Indicador",
    )
    periodo = models.DateField("Período")
    valor_calculado = models.DecimalField(
        "Valor calculado", max_digits=15, decimal_places=4
    )
    data_calculo = models.DateTimeField("Data do cálculo", auto_now_add=True)

    class Meta:
        verbose_name = "Medição de indicador"
        verbose_name_plural = "Medições de indicador"
        ordering = ["indicador", "periodo"]

    def __str__(self):
        return f"{self.indicador} em {self.periodo}: {self.valor_calculado}"
