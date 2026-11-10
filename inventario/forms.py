from django import forms

from .models import ItemInventario, Segmento


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
        item = super().save(commit=commit)
        if commit:
            self._salvar_segmentos(item)
        return item

    def _salvar_segmentos(self, item):
        from .models import Participa

        selecionados = set(self.cleaned_data.get("segmentos", []))
        atuais = set(Segmento.objects.filter(participa__item=item))
        for seg in selecionados - atuais:
            Participa.objects.get_or_create(item=item, segmento=seg)
        Participa.objects.filter(item=item).exclude(
            segmento__in=selecionados
        ).delete()
