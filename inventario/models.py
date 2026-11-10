"""Modelo de dados do Inventário Turístico (Base de Dados Principal).

Implementa fielmente o Modelo Lógico Relacional do OTO: Segmento,
Item_Inventario, Campo_Segmento, Preenchimento, Participa, Profissional_Turismo,
Contato, Cadastur, Cnae e tabelas de vínculo, com as restrições de integridade
documentadas (soft delete, faixas de coordenadas, exclusividade de Contato/
Cadastur e chave composta de Preenchimento).
"""
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class StatusItem(models.TextChoices):
    ATIVO = "ativo", "Ativo"
    INATIVO = "inativo", "Inativo"


class ItemAtivoManager(models.Manager):
    """Listagem padrão mostra apenas itens ativos (BDP05 / RN01)."""

    def get_queryset(self):
        return super().get_queryset().filter(status=StatusItem.ATIVO)


class Segmento(models.Model):
    """Segmento/categoria do inventário (ex.: Hospedagem, Alimentação)."""

    nome = models.CharField("Nome", max_length=120, unique=True)
    descricao = models.TextField("Descrição", blank=True)

    class Meta:
        verbose_name = "Segmento"
        verbose_name_plural = "Segmentos"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Cnae(models.Model):
    """Classificação Nacional de Atividades Econômicas."""

    codigo = models.CharField("Código", max_length=15, primary_key=True)
    descricao = models.CharField("Descrição", max_length=255)

    class Meta:
        verbose_name = "CNAE"
        verbose_name_plural = "CNAEs"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} - {self.descricao}"


class ItemInventario(models.Model):
    """Estabelecimento ou atrativo turístico (núcleo do inventário)."""

    nome = models.CharField("Nome", max_length=255)
    razao_social = models.CharField("Razão social", max_length=255, blank=True)
    tipo_documento = models.CharField("Tipo de documento", max_length=20, blank=True)
    documento = models.CharField("Documento", max_length=30, blank=True)
    endereco = models.CharField("Endereço", max_length=255, blank=True)
    bairro = models.CharField("Bairro", max_length=120, blank=True)
    latitude = models.DecimalField(
        "Latitude",
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    longitude = models.DecimalField(
        "Longitude",
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    status = models.CharField(
        "Status", max_length=10, choices=StatusItem.choices, default=StatusItem.ATIVO
    )
    criado_em = models.DateTimeField("Criado em", auto_now_add=True)
    atualizado_em = models.DateTimeField("Atualizado em", auto_now=True)

    segmentos = models.ManyToManyField(
        Segmento, through="Participa", related_name="itens", verbose_name="Segmentos"
    )
    atividades = models.ManyToManyField(
        Cnae, through="PossuiAtividade", related_name="itens", verbose_name="Atividades"
    )

    objects = models.Manager()  # todos os itens
    ativos = ItemAtivoManager()  # apenas ativos (listagem padrão)

    class Meta:
        verbose_name = "Item do Inventário"
        verbose_name_plural = "Itens do Inventário"
        ordering = ["nome"]
        constraints = [
            models.CheckConstraint(
                name="item_latitude_valida",
                condition=(
                    models.Q(latitude__isnull=True)
                    | models.Q(latitude__gte=-90, latitude__lte=90)
                ),
            ),
            models.CheckConstraint(
                name="item_longitude_valida",
                condition=(
                    models.Q(longitude__isnull=True)
                    | models.Q(longitude__gte=-180, longitude__lte=180)
                ),
            ),
        ]

    def __str__(self):
        return self.nome

    @property
    def esta_ativo(self) -> bool:
        return self.status == StatusItem.ATIVO


class Participa(models.Model):
    """Vínculo Item <-> Segmento, com classificação opcional no segmento."""

    item = models.ForeignKey(
        ItemInventario, on_delete=models.CASCADE, verbose_name="Item"
    )
    segmento = models.ForeignKey(
        Segmento, on_delete=models.CASCADE, verbose_name="Segmento"
    )
    classificacao = models.CharField("Classificação", max_length=120, blank=True)

    class Meta:
        verbose_name = "Participação em segmento"
        verbose_name_plural = "Participações em segmentos"
        constraints = [
            models.UniqueConstraint(
                fields=["item", "segmento"], name="participa_item_segmento_unico"
            )
        ]

    def __str__(self):
        return f"{self.item} em {self.segmento}"


class CampoSegmento(models.Model):
    """Campo específico de um segmento (campos dinâmicos por categoria)."""

    class TipoDado(models.TextChoices):
        TEXTO = "texto", "Texto"
        NUMERO = "numero", "Número"
        DATA = "data", "Data"
        BOOLEANO = "booleano", "Sim/Não"

    segmento = models.ForeignKey(
        Segmento,
        on_delete=models.CASCADE,
        related_name="campos",
        verbose_name="Segmento",
    )
    nome = models.CharField("Nome do campo", max_length=120)
    tipo_dado = models.CharField(
        "Tipo de dado", max_length=20, choices=TipoDado.choices, default=TipoDado.TEXTO
    )
    obrigatorio = models.BooleanField("Obrigatório", default=False)

    class Meta:
        verbose_name = "Campo de segmento"
        verbose_name_plural = "Campos de segmento"
        ordering = ["segmento", "nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["segmento", "nome"], name="campo_segmento_nome_unico"
            )
        ]

    def __str__(self):
        return f"{self.nome} ({self.segmento})"


class Preenchimento(models.Model):
    """Valor informado para um campo de segmento de um item (PK composta)."""

    item = models.ForeignKey(
        ItemInventario,
        on_delete=models.CASCADE,
        related_name="preenchimentos",
        verbose_name="Item",
    )
    campo = models.ForeignKey(
        CampoSegmento,
        on_delete=models.CASCADE,
        related_name="preenchimentos",
        verbose_name="Campo",
    )
    valor = models.TextField("Valor", blank=True)

    class Meta:
        verbose_name = "Preenchimento"
        verbose_name_plural = "Preenchimentos"
        constraints = [
            models.UniqueConstraint(
                fields=["item", "campo"], name="preenchimento_item_campo_unico"
            )
        ]

    def clean(self):
        # O campo deve pertencer a um segmento ao qual o item está vinculado.
        if self.item_id and self.campo_id:
            vinculado = Participa.objects.filter(
                item_id=self.item_id, segmento_id=self.campo.segmento_id
            ).exists()
            if not vinculado:
                raise ValidationError(
                    "O campo pertence a um segmento ao qual o item não está vinculado."
                )

    def __str__(self):
        return f"{self.item} / {self.campo}: {self.valor}"


class PossuiAtividade(models.Model):
    """Vínculo Item <-> CNAE."""

    item = models.ForeignKey(ItemInventario, on_delete=models.CASCADE)
    cnae = models.ForeignKey(Cnae, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Atividade do item"
        verbose_name_plural = "Atividades do item"
        constraints = [
            models.UniqueConstraint(
                fields=["item", "cnae"], name="possui_atividade_unico"
            )
        ]


class ProfissionalTurismo(models.Model):
    """Pessoa física (ex.: guia de turismo)."""

    nome = models.CharField("Nome", max_length=255)
    cpf = models.CharField("CPF", max_length=14, blank=True)
    endereco = models.CharField("Endereço", max_length=255, blank=True)
    classificacao = models.CharField("Classificação", max_length=120, blank=True)

    itens = models.ManyToManyField(
        ItemInventario,
        through="VinculoProfissionalItem",
        related_name="profissionais",
        verbose_name="Itens vinculados",
    )

    class Meta:
        verbose_name = "Profissional de turismo"
        verbose_name_plural = "Profissionais de turismo"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class CategoriaAtuacaoProfissional(models.Model):
    """Categoria de atuação de um profissional (atributo multivalorado)."""

    profissional = models.ForeignKey(
        ProfissionalTurismo,
        on_delete=models.CASCADE,
        related_name="categorias_atuacao",
        verbose_name="Profissional",
    )
    categoria_atuacao = models.CharField("Categoria de atuação", max_length=120)

    class Meta:
        verbose_name = "Categoria de atuação"
        verbose_name_plural = "Categorias de atuação"
        constraints = [
            models.UniqueConstraint(
                fields=["profissional", "categoria_atuacao"],
                name="categoria_atuacao_unica",
            )
        ]

    def __str__(self):
        return self.categoria_atuacao


class VinculoProfissionalItem(models.Model):
    """Vínculo Profissional <-> Item."""

    profissional = models.ForeignKey(ProfissionalTurismo, on_delete=models.CASCADE)
    item = models.ForeignKey(ItemInventario, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Vínculo profissional-item"
        verbose_name_plural = "Vínculos profissional-item"
        constraints = [
            models.UniqueConstraint(
                fields=["profissional", "item"], name="vinculo_prof_item_unico"
            )
        ]


class _AssociadoItemOuProfissional(models.Model):
    """Base abstrata: registro associado a UM item OU UM profissional (XOR)."""

    item = models.ForeignKey(
        ItemInventario,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Item",
    )
    profissional = models.ForeignKey(
        ProfissionalTurismo,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Profissional",
    )

    class Meta:
        abstract = True

    def clean(self):
        tem_item = self.item_id is not None
        tem_prof = self.profissional_id is not None
        if tem_item == tem_prof:
            raise ValidationError(
                "Associe exatamente um entre Item e Profissional (não ambos nem nenhum)."
            )


class Contato(_AssociadoItemOuProfissional):
    """Telefone/e-mail/canal associado a um item ou profissional."""

    tipo = models.CharField("Tipo", max_length=40)
    valor = models.CharField("Valor", max_length=255)
    finalidade = models.CharField("Finalidade", max_length=120, blank=True)

    class Meta:
        verbose_name = "Contato"
        verbose_name_plural = "Contatos"
        constraints = [
            models.CheckConstraint(
                name="contato_item_xor_profissional",
                condition=(
                    models.Q(item__isnull=False, profissional__isnull=True)
                    | models.Q(item__isnull=True, profissional__isnull=False)
                ),
            )
        ]

    def __str__(self):
        return f"{self.tipo}: {self.valor}"


class Cadastur(_AssociadoItemOuProfissional):
    """Registro Cadastur associado a um item ou profissional."""

    numero = models.CharField("Número", max_length=40)
    tipo = models.CharField("Tipo", max_length=40, blank=True)
    situacao = models.CharField("Situação", max_length=40, blank=True)
    vencimento = models.DateField("Vencimento", null=True, blank=True)

    class Meta:
        verbose_name = "Cadastur"
        verbose_name_plural = "Registros Cadastur"
        constraints = [
            models.CheckConstraint(
                name="cadastur_item_xor_profissional",
                condition=(
                    models.Q(item__isnull=False, profissional__isnull=True)
                    | models.Q(item__isnull=True, profissional__isnull=False)
                ),
            )
        ]

    def __str__(self):
        return f"Cadastur {self.numero}"
