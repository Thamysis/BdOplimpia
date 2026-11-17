from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
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
from auditoria.services import (
    registrar_criacao, registrar_edicao, registrar_relacao, snapshot, snapshot_relacoes,
)

from .forms import CadasturItemFormSet, ContatoItemFormSet, DadosComplementaresForm, ItemInventarioForm
from .models import (
    CampoSegmento, Cnae, ItemInventario, Participa, ProfissionalTurismo, Segmento, StatusItem,
)

def itens_acessiveis_por(usuario):
    """Retorna os itens que o usuário pode acessar pelo escopo de Gerencia."""
    qs = ItemInventario.objects.all()

    if not usuario.eh_administrador and usuario.gerencias.exists():
        qs = qs.filter(gerencias__usuario=usuario)

    return qs.distinct()

class ItemListView(LoginRequiredMixin, ListView):
    """BDP04 — consulta e filtro. Lista apenas itens ativos por padrão."""

    template_name = "inventario/item_lista.html"
    context_object_name = "itens"
    paginate_by = 20

    def get_queryset(self):
        qs = itens_acessiveis_por(self.request.user)
        status = self.request.GET.get("status", "").strip()
        incluir_inativos = self.request.GET.get("incluir_inativos") == "1"
        if status in (StatusItem.ATIVO, StatusItem.INATIVO):
            qs = qs.filter(status=status)
        elif not incluir_inativos:
            qs = qs.filter(status=StatusItem.ATIVO)

        nome = self.request.GET.get("nome", "").strip()
        if nome:
            qs = qs.filter(nome__icontains=nome)

        segmento_id = self.request.GET.get("segmento", "").strip()
        if segmento_id:
            qs = qs.filter(participa__segmento_id=segmento_id)

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
        parametros = self.request.GET.copy()
        parametros.pop("page", None)
        ctx["parametros_paginacao"] = parametros.urlencode()
        return ctx


class ItemDetailView(LoginRequiredMixin, DetailView):
    model = ItemInventario
    template_name = "inventario/item_detalhe.html"
    context_object_name = "item"

    def get_queryset(self):
        return itens_acessiveis_por(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["historico"] = self.object.historico.all()
        ctx["segmentos_item"] = Segmento.objects.filter(participa__item=self.object)
        ctx["preenchimentos"] = self.object.preenchimentos.select_related("campo", "campo__segmento")
        ctx["contatos"] = self.object.contato_set.all()
        ctx["cadastur"] = self.object.cadastur_set.all()
        ctx["cnaes"] = self.object.atividades.all()
        ctx["profissionais"] = self.object.profissionais.all()
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
        relacoes_antes = snapshot_relacoes(self.object)
        response = super().form_valid(form)
        registrar_edicao(self.object, anterior, usuario=self.request.user)
        relacoes_depois = snapshot_relacoes(self.object)
        for campo in ("segmentos", "campos de segmento"):
            registrar_relacao(
                self.object, campo, relacoes_antes[campo], relacoes_depois[campo],
                usuario=self.request.user,
            )
        messages.success(self.request, "Item atualizado com sucesso.")
        return response

    def get_success_url(self):
        return reverse("inventario:detalhe", args=[self.object.pk])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Editar item"
        return ctx
    
    def get_queryset(self):
        return itens_acessiveis_por(self.request.user)

class ItemInativarView(EditaInventarioRequiredMixin, View):
    """BDP05 — inativa (soft delete) preservando histórico e vínculos."""

    def post(self, request, pk):
        item = get_object_or_404(
            itens_acessiveis_por(request.user),
            pk=pk,
        )
        if item.status == StatusItem.ATIVO:
            anterior = snapshot(item)
            item.status = StatusItem.INATIVO
            item.save()
            registrar_edicao(item, anterior, usuario=request.user)
            messages.info(request, f"Item '{item.nome}' inativado.")
        return redirect("inventario:detalhe", pk=pk)


class ItemReativarView(EditaInventarioRequiredMixin, View):
    def post(self, request, pk):
        item = get_object_or_404(
            itens_acessiveis_por(request.user),
            pk=pk,
        )
        if item.status == StatusItem.INATIVO:
            anterior = snapshot(item)
            item.status = StatusItem.ATIVO
            item.save()
            registrar_edicao(item, anterior, usuario=request.user)
            messages.info(request, f"Item '{item.nome}' reativado.")
        return redirect("inventario:detalhe", pk=pk)


class DadosComplementaresView(EditaInventarioRequiredMixin, View):
    """Edita os dados do Inventário que dependem do segmento e seus vínculos."""

    template_name = "inventario/dados_complementares.html"

    def _formularios(self, item, dados=None):
        return (
            DadosComplementaresForm(dados, item=item),
            ContatoItemFormSet(dados, instance=item, prefix="contatos"),
            CadasturItemFormSet(dados, instance=item, prefix="cadastur"),
        )

    def _render(self, request, item, form, contatos, cadastur):
        return render(request, self.template_name, {
            "item": item, "form": form, "contatos_formset": contatos,
            "cadastur_formset": cadastur,
        })

    def get(self, request, pk):
        item = get_object_or_404(
            itens_acessiveis_por(request.user),
            pk=pk,
        )
        return self._render(request, item, *self._formularios(item))

    def post(self, request, pk):
        item = get_object_or_404(
            itens_acessiveis_por(request.user),
            pk=pk,
        )
        form, contatos, cadastur = self._formularios(item, request.POST)
        if not all((form.is_valid(), contatos.is_valid(), cadastur.is_valid())):
            return self._render(request, item, form, contatos, cadastur)
        with transaction.atomic():
            anterior = snapshot_relacoes(item)
            form.save()
            contatos.save()
            cadastur.save()
            atual = snapshot_relacoes(item)
            for campo in anterior:
                registrar_relacao(item, campo, anterior[campo], atual[campo], usuario=request.user)
        messages.success(request, "Dados complementares atualizados.")
        return redirect("inventario:detalhe", pk=item.pk)


class CatalogosView(EditaInventarioRequiredMixin, TemplateView):
    template_name = "inventario/catalogos.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["segmentos"] = Segmento.objects.all()
        ctx["campos"] = CampoSegmento.objects.select_related("segmento")
        ctx["cnaes"] = Cnae.objects.all()
        ctx["profissionais"] = ProfissionalTurismo.objects.all()
        return ctx


class CadastroCatalogoMixin(EditaInventarioRequiredMixin):
    template_name = "inventario/catalogo_form.html"
    success_url = reverse_lazy("inventario:catalogos")


class SegmentoCreateView(CadastroCatalogoMixin, CreateView):
    model = Segmento
    fields = ["nome", "descricao"]
    titulo = "Novo segmento"


class CampoSegmentoCreateView(CadastroCatalogoMixin, CreateView):
    model = CampoSegmento
    fields = ["segmento", "nome", "tipo_dado", "obrigatorio"]
    titulo = "Novo campo de segmento"


class CnaeCreateView(CadastroCatalogoMixin, CreateView):
    model = Cnae
    fields = ["codigo", "descricao"]
    titulo = "Nova atividade CNAE"


class ProfissionalCreateView(CadastroCatalogoMixin, CreateView):
    model = ProfissionalTurismo
    fields = ["nome", "cpf", "endereco", "classificacao"]
    titulo = "Novo profissional"


class RelatoriosView(LoginRequiredMixin, TemplateView):
    """Relatórios visuais do Inventário: distribuição por segmento e por status."""

    template_name = "inventario/relatorios.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        itens = itens_acessiveis_por(self.request.user)

        total = itens.count()
        ativos = itens.filter(status=StatusItem.ATIVO).count()
        inativos = itens.filter(status=StatusItem.INATIVO).count()

        # Itens por segmento (ativos e inativos), ordenado pelo total.
        por_segmento = list(
            Segmento.objects.annotate(
                total=Count(
                    "participa__item",
                    filter=Q(participa__item__in=itens),
                    distinct=True,
                ),
                ativos=Count(
                    "participa__item",
                    filter=Q(
                        participa__item__in=itens,
                        participa__item__status=StatusItem.ATIVO,
                    ),
                    distinct=True,
                ),
            )
            .filter(total__gt=0)
            .order_by("-total", "nome")
        )

        # Itens sem nenhum segmento vinculado.
        sem_segmento = itens.filter(participa__isnull=True).count()

        pct_ativos = (ativos / total * 100) if total else 0
        pct_inativos = (inativos / total * 100) if total else 0
        ctx.update(
            {
                "total": total,
                "ativos": ativos,
                "inativos": inativos,
                "pct_ativos": pct_ativos,
                "pct_inativos": pct_inativos,
                "pct_ativos_css": f"{pct_ativos:.2f}",
                "pct_inativos_css": f"{pct_inativos:.2f}",
                "por_segmento": por_segmento,
                "sem_segmento": sem_segmento,
            }
        )
        return ctx
