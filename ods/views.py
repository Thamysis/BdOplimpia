from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView, View

from acesso.permissions import ConsultaIndicadoresRequiredMixin

from .forms import DadoPesquisaForm, IndicadorODSForm
from .models import IndicadorODS, MedicaoIndicador


class IndicadorListView(ConsultaIndicadoresRequiredMixin, ListView):
    model = IndicadorODS
    template_name = "ods/indicador_lista.html"
    context_object_name = "indicadores"


class IndicadorCreateView(ConsultaIndicadoresRequiredMixin, CreateView):
    """BDP08 — cadastro de indicador ODS (nome obrigatório)."""

    model = IndicadorODS
    form_class = IndicadorODSForm
    template_name = "ods/indicador_form.html"

    def form_valid(self, form):
        messages.success(self.request, "Indicador cadastrado com sucesso.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("ods:indicador_detalhe", args=[self.object.pk])


class IndicadorDetailView(ConsultaIndicadoresRequiredMixin, DetailView):
    """BDP12 — histórico de medições ordenado por período (asc)."""

    model = IndicadorODS
    template_name = "ods/indicador_detalhe.html"
    context_object_name = "indicador"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["medicoes"] = self.object.medicoes.order_by("periodo")
        ctx["dados_pesquisa"] = self.object.dados_pesquisa.order_by("data_referencia")
        ctx["itens_vinculados"] = self.object.itens_vinculados.select_related("item")
        return ctx


class DadoPesquisaCreateView(ConsultaIndicadoresRequiredMixin, CreateView):
    """BDP09 — registro de dado de pesquisa (indicador obrigatório)."""

    model = IndicadorODS
    form_class = DadoPesquisaForm
    template_name = "ods/dado_pesquisa_form.html"

    def form_valid(self, form):
        self.dado = form.save()
        messages.success(self.request, "Dado de pesquisa registrado.")
        return redirect("ods:indicador_detalhe", pk=self.dado.indicador_id)


class CalcularMedicaoView(ConsultaIndicadoresRequiredMixin, View):
    """BDP10 — recalcula a medição do indicador conforme a regra documentada."""

    def post(self, request, pk):
        indicador = get_object_or_404(IndicadorODS, pk=pk)
        valor = indicador.calcular()
        MedicaoIndicador.objects.create(
            indicador=indicador,
            periodo=timezone.now().date(),
            valor_calculado=valor,
        )
        messages.success(request, f"Medição calculada: {valor}.")
        return redirect("ods:indicador_detalhe", pk=pk)
