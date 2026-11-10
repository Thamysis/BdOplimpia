from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
    View,
)

from acesso.permissions import EditaInventarioRequiredMixin
from auditoria.services import registrar_criacao, registrar_edicao, snapshot

from .forms import ItemInventarioForm
from .models import ItemInventario, Participa, Segmento, StatusItem


class ItemListView(LoginRequiredMixin, ListView):
    """BDP04 — consulta e filtro. Lista apenas itens ativos por padrão."""

    template_name = "inventario/item_lista.html"
    context_object_name = "itens"
    paginate_by = 20

    def get_queryset(self):
        qs = ItemInventario.objects.all()
        incluir_inativos = self.request.GET.get("incluir_inativos") == "1"
        if not incluir_inativos:
            qs = qs.filter(status=StatusItem.ATIVO)

        nome = self.request.GET.get("nome", "").strip()
        if nome:
            qs = qs.filter(nome__icontains=nome)

        segmento_id = self.request.GET.get("segmento", "").strip()
        if segmento_id:
            qs = qs.filter(participa__segmento_id=segmento_id)

        status = self.request.GET.get("status", "").strip()
        if status in (StatusItem.ATIVO, StatusItem.INATIVO):
            qs = qs.filter(status=status)

        return qs.distinct()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["segmentos"] = Segmento.objects.all()
        ctx["filtros"] = {
            "nome": self.request.GET.get("nome", ""),
            "segmento": self.request.GET.get("segmento", ""),
            "status": self.request.GET.get("status", ""),
            "incluir_inativos": self.request.GET.get("incluir_inativos", ""),
        }
        ctx["status_choices"] = StatusItem.choices
        return ctx


class ItemDetailView(LoginRequiredMixin, DetailView):
    model = ItemInventario
    template_name = "inventario/item_detalhe.html"
    context_object_name = "item"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["historico"] = self.object.historico.all()
        ctx["segmentos_item"] = Segmento.objects.filter(participa__item=self.object)
        return ctx


class ItemCreateView(EditaInventarioRequiredMixin, CreateView):
    """BDP02 — cadastro de item com validação de obrigatórios."""

    model = ItemInventario
    form_class = ItemInventarioForm
    template_name = "inventario/item_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        registrar_criacao(self.object, usuario=self.request.user)
        messages.success(self.request, "Item cadastrado com sucesso.")
        return response

    def get_success_url(self):
        return reverse("inventario:detalhe", args=[self.object.pk])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Cadastrar item"
        return ctx


class ItemUpdateView(EditaInventarioRequiredMixin, UpdateView):
    """BDP03 — edição de item, com registro de histórico por campo alterado."""

    model = ItemInventario
    form_class = ItemInventarioForm
    template_name = "inventario/item_form.html"

    def get_initial(self):
        initial = super().get_initial()
        initial["segmentos"] = Segmento.objects.filter(participa__item=self.object)
        return initial

    def form_valid(self, form):
        anterior = snapshot(self.get_object())
        response = super().form_valid(form)
        registrar_edicao(self.object, anterior, usuario=self.request.user)
        messages.success(self.request, "Item atualizado com sucesso.")
        return response

    def get_success_url(self):
        return reverse("inventario:detalhe", args=[self.object.pk])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Editar item"
        return ctx


class ItemInativarView(EditaInventarioRequiredMixin, View):
    """BDP05 — inativa (soft delete) preservando histórico e vínculos."""

    def post(self, request, pk):
        item = get_object_or_404(ItemInventario, pk=pk)
        if item.status == StatusItem.ATIVO:
            anterior = snapshot(item)
            item.status = StatusItem.INATIVO
            item.save()
            registrar_edicao(item, anterior, usuario=request.user)
            messages.info(request, f"Item '{item.nome}' inativado.")
        return redirect("inventario:detalhe", pk=pk)


class ItemReativarView(EditaInventarioRequiredMixin, View):
    def post(self, request, pk):
        item = get_object_or_404(ItemInventario, pk=pk)
        if item.status == StatusItem.INATIVO:
            anterior = snapshot(item)
            item.status = StatusItem.ATIVO
            item.save()
            registrar_edicao(item, anterior, usuario=request.user)
            messages.info(request, f"Item '{item.nome}' reativado.")
        return redirect("inventario:detalhe", pk=pk)


class RelatoriosView(LoginRequiredMixin, TemplateView):
    """Relatórios visuais do Inventário: distribuição por segmento e por status."""

    template_name = "inventario/relatorios.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        total = ItemInventario.objects.count()
        ativos = ItemInventario.objects.filter(status=StatusItem.ATIVO).count()
        inativos = ItemInventario.objects.filter(status=StatusItem.INATIVO).count()

        # Itens por segmento (ativos e inativos), ordenado pelo total.
        por_segmento = list(
            Segmento.objects.annotate(
                total=Count("participa__item", distinct=True),
                ativos=Count(
                    "participa__item",
                    filter=Q(participa__item__status=StatusItem.ATIVO),
                    distinct=True,
                ),
            ).order_by("-total", "nome")
        )
        max_segmento = max([s.total for s in por_segmento], default=0)
        for s in por_segmento:
            s.percentual = (s.total / max_segmento * 100) if max_segmento else 0

        # Itens sem nenhum segmento vinculado.
        sem_segmento = ItemInventario.objects.filter(participa__isnull=True).count()

        ctx.update(
            {
                "total": total,
                "ativos": ativos,
                "inativos": inativos,
                "pct_ativos": (ativos / total * 100) if total else 0,
                "pct_inativos": (inativos / total * 100) if total else 0,
                "por_segmento": por_segmento,
                "sem_segmento": sem_segmento,
            }
        )
        return ctx
