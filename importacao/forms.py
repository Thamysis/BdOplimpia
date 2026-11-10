from django import forms

from .models import FonteDados


class ImportacaoForm(forms.Form):
    arquivo = forms.FileField(
        label="Arquivo do Inventário (CSV, XLSX ou ODS)",
        widget=forms.ClearableFileInput(attrs={"class": "campo", "accept": ".csv,.xlsx,.ods"}),
    )
    fonte = forms.ModelChoiceField(
        queryset=FonteDados.objects.all(),
        required=False,
        label="Fonte de dados",
        widget=forms.Select(attrs={"class": "campo"}),
    )

    def clean_arquivo(self):
        arquivo = self.cleaned_data["arquivo"]
        if arquivo.size > 10 * 1024 * 1024:
            raise forms.ValidationError("Arquivo maior que o limite de 10 MB.")
        return arquivo


class ImportacaoOficialForm(forms.Form):
    """Importa uma aba de categoria da planilha oficial (um segmento)."""

    segmento = forms.CharField(
        label="Categoria/Segmento (nome da aba)",
        widget=forms.TextInput(attrs={"class": "campo", "placeholder": "Ex.: Meios de Hospedagem"}),
    )
    arquivo = forms.FileField(
        label="Arquivo da aba (CSV, XLSX ou ODS)",
        widget=forms.ClearableFileInput(attrs={"class": "campo", "accept": ".csv,.xlsx,.ods"}),
    )

    def clean_arquivo(self):
        arquivo = self.cleaned_data["arquivo"]
        if arquivo.size > 10 * 1024 * 1024:
            raise forms.ValidationError("Arquivo maior que o limite de 10 MB.")
        return arquivo
