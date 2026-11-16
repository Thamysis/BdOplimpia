from django import forms
from django.db import transaction

from inventario.models import ItemInventario

from .models import DadoPesquisaODS, IndicadorODS, ODS, ODSIndicador, VinculoInventarioIndicador


class IndicadorODSForm(forms.ModelForm):
    objetivos = forms.ModelMultipleChoiceField(
        queryset=ODS.objects.all(), required=False, label="Objetivos ODS",
        widget=forms.CheckboxSelectMultiple,
    )
    itens = forms.ModelMultipleChoiceField(
        queryset=ItemInventario.objects.all(), required=False,
        label="Itens do Inventário vinculados", widget=forms.SelectMultiple,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["objetivos"].initial = self.instance.ods.all()
            self.fields["itens"].initial = ItemInventario.objects.filter(
                indicadores_vinculados__indicador=self.instance
            )

    @transaction.atomic
    def save(self, commit=True):
        indicador = super().save(commit=commit)
        if commit:
            objetivos = set(self.cleaned_data["objetivos"].values_list("pk", flat=True))
            itens = set(self.cleaned_data["itens"].values_list("pk", flat=True))
            ODSIndicador.objects.filter(indicador=indicador).exclude(ods_id__in=objetivos).delete()
            VinculoInventarioIndicador.objects.filter(indicador=indicador).exclude(item_id__in=itens).delete()
            for pk in objetivos:
                ODSIndicador.objects.get_or_create(indicador=indicador, ods_id=pk)
            for pk in itens:
                VinculoInventarioIndicador.objects.get_or_create(indicador=indicador, item_id=pk)
        return indicador

    class Meta:
        model = IndicadorODS
        fields = [
            "nome",
            "descricao",
            "meta",
            "regra_calculo",
            "regra_campo",
            "regra_valor",
            "regra_descricao",
        ]
        widgets = {
            "nome": forms.TextInput(attrs={"class": "campo"}),
            "descricao": forms.Textarea(attrs={"class": "campo", "rows": 3}),
            "meta": forms.TextInput(attrs={"class": "campo"}),
            "regra_campo": forms.TextInput(attrs={"class": "campo"}),
            "regra_valor": forms.TextInput(attrs={"class": "campo"}),
            "regra_descricao": forms.Textarea(attrs={"class": "campo", "rows": 2}),
        }


class DadoPesquisaForm(forms.ModelForm):
    class Meta:
        model = DadoPesquisaODS
        fields = ["indicador", "origem_pesquisa", "data_referencia", "valor", "observacao"]
        widgets = {
            "origem_pesquisa": forms.TextInput(attrs={"class": "campo"}),
            "data_referencia": forms.DateInput(
                attrs={"class": "campo", "type": "date"}
            ),
            "valor": forms.NumberInput(attrs={"class": "campo", "step": "0.0001"}),
            "observacao": forms.Textarea(attrs={"class": "campo", "rows": 2}),
        }
