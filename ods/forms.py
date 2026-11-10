from django import forms

from .models import DadoPesquisaODS, IndicadorODS


class IndicadorODSForm(forms.ModelForm):
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
