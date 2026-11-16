from django import forms

from django.forms import inlineformset_factory

from .models import (
    Cadastur, CampoSegmento, Cnae, Contato, ItemInventario, PossuiAtividade,
    Preenchimento, ProfissionalTurismo, Segmento, VinculoProfissionalItem,
)


class ItemInventarioForm(forms.ModelForm):
    segmentos = forms.ModelMultipleChoiceField(
        queryset=Segmento.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Segmentos",
    )

    class Meta:
        model = ItemInventario
        fields = [
            "nome",
            "razao_social",
            "tipo_documento",
            "documento",
            "endereco",
            "bairro",
            "latitude",
            "longitude",
            "segmentos",
        ]
        widgets = {
            "nome": forms.TextInput(attrs={"class": "campo"}),
            "razao_social": forms.TextInput(attrs={"class": "campo"}),
            "tipo_documento": forms.TextInput(attrs={"class": "campo"}),
            "documento": forms.TextInput(attrs={"class": "campo"}),
            "endereco": forms.TextInput(attrs={"class": "campo"}),
            "bairro": forms.TextInput(attrs={"class": "campo"}),
            "latitude": forms.NumberInput(attrs={"class": "campo", "step": "0.000001"}),
            "longitude": forms.NumberInput(attrs={"class": "campo", "step": "0.000001"}),
        }

    def save(self, commit=True):
        segmentos_anteriores = set(self.instance.segmentos.values_list("pk", flat=True)) if self.instance.pk else set()
        item = super().save(commit=commit)
        if commit:
            self._salvar_segmentos(item, segmentos_anteriores)
        return item

    def _salvar_segmentos(self, item, segmentos_anteriores):
        from .models import Participa

        selecionados = set(self.cleaned_data.get("segmentos", []))
        atuais = set(Segmento.objects.filter(participa__item=item))
        for seg in selecionados - atuais:
            Participa.objects.get_or_create(item=item, segmento=seg)
        removidos = segmentos_anteriores - {seg.pk for seg in selecionados}
        if removidos:
            Preenchimento.objects.filter(item=item, campo__segmento_id__in=removidos).delete()
        Participa.objects.filter(item=item).exclude(
            segmento__in=selecionados
        ).delete()


class DadosComplementaresForm(forms.Form):
    cnaes = forms.ModelMultipleChoiceField(
        queryset=Cnae.objects.all(), required=False, label="Atividades CNAE",
        widget=forms.SelectMultiple,
    )
    profissionais = forms.ModelMultipleChoiceField(
        queryset=ProfissionalTurismo.objects.all(), required=False,
        label="Profissionais vinculados", widget=forms.SelectMultiple,
    )

    def __init__(self, *args, item, **kwargs):
        super().__init__(*args, **kwargs)
        self.item = item
        self.fields["cnaes"].initial = item.atividades.all()
        self.fields["profissionais"].initial = item.profissionais.all()
        self.campos = list(CampoSegmento.objects.filter(segmento__participa__item=item).distinct())
        valores = dict(Preenchimento.objects.filter(item=item).values_list("campo_id", "valor"))
        for campo in self.campos:
            chave = f"campo_{campo.pk}"
            tipo = campo.tipo_dado
            if tipo == CampoSegmento.TipoDado.NUMERO:
                field = forms.DecimalField(required=campo.obrigatorio, label=campo.nome)
            elif tipo == CampoSegmento.TipoDado.DATA:
                field = forms.DateField(
                    required=campo.obrigatorio, label=campo.nome,
                    widget=forms.DateInput(attrs={"type": "date"}),
                )
            elif tipo == CampoSegmento.TipoDado.BOOLEANO:
                field = forms.ChoiceField(
                    choices=[("", "—"), ("Sim", "Sim"), ("Não", "Não")],
                    required=campo.obrigatorio, label=campo.nome,
                )
            else:
                field = forms.CharField(required=campo.obrigatorio, label=campo.nome)
            self.fields[chave] = field
            self.fields[chave].initial = valores.get(campo.pk, "")

    def save(self):
        selecionados_cnae = set(self.cleaned_data["cnaes"].values_list("pk", flat=True))
        selecionados_prof = set(self.cleaned_data["profissionais"].values_list("pk", flat=True))
        PossuiAtividade.objects.filter(item=self.item).exclude(cnae_id__in=selecionados_cnae).delete()
        VinculoProfissionalItem.objects.filter(item=self.item).exclude(profissional_id__in=selecionados_prof).delete()
        for pk in selecionados_cnae:
            PossuiAtividade.objects.get_or_create(item=self.item, cnae_id=pk)
        for pk in selecionados_prof:
            VinculoProfissionalItem.objects.get_or_create(item=self.item, profissional_id=pk)
        for campo in self.campos:
            valor = self.cleaned_data[f"campo_{campo.pk}"]
            if valor is None or valor == "":
                Preenchimento.objects.filter(item=self.item, campo=campo).delete()
            else:
                if hasattr(valor, "isoformat"):
                    valor = valor.isoformat()
                Preenchimento.objects.update_or_create(
                    item=self.item, campo=campo, defaults={"valor": str(valor)}
                )


ContatoItemFormSet = inlineformset_factory(
    ItemInventario, Contato, fk_name="item", fields=("tipo", "valor", "finalidade"),
    extra=1, can_delete=True,
)
CadasturItemFormSet = inlineformset_factory(
    ItemInventario, Cadastur, fk_name="item",
    fields=("numero", "tipo", "situacao", "vencimento"), extra=1, can_delete=True,
)
