import base64

from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.generic import DetailView, FormView, ListView, View

from acesso.permissions import ImportaRequiredMixin

from . import oficial, services
from .forms import ImportacaoForm, ImportacaoOficialForm
from .models import FonteDados, Importacao
from .services import ArquivoNaoSuportado

SESSAO_CHAVE = "importacao_preview"


class ImportacaoView(ImportaRequiredMixin, FormView):
    """BDP01 / BDP11 — passo 1: upload gera a PRÉVIA classificada (sem gravar)."""

    template_name = "importacao/importar.html"
    form_class = ImportacaoForm

    def form_valid(self, form):
        arquivo = form.cleaned_data["arquivo"]
        conteudo = arquivo.read()
        nome = arquivo.name
        fonte = form.cleaned_data.get("fonte")

        try:
            resultado = services.gerar_previa(conteudo, nome)
        except (ArquivoNaoSuportado, UnicodeDecodeError) as exc:
            form.add_error("arquivo", str(exc) or "Não foi possível ler o arquivo.")
            return self.form_invalid(form)

        # Guarda o arquivo na sessão para a confirmação (passo 2).
        self.request.session[SESSAO_CHAVE] = {
            "conteudo_b64": base64.b64encode(conteudo).decode("ascii"),
            "nome": nome,
            "fonte_id": fonte.pk if fonte else None,
        }
        return render(
            self.request,
            "importacao/previa.html",
            {"resultado": resultado, "nome_arquivo": nome, "fonte": fonte},
        )


class ImportacaoConfirmarView(ImportaRequiredMixin, View):
    """Passo 2: confirma a prévia e grava os itens aceitos uma única vez (BDP01)."""

    def post(self, request):
        dados = request.session.get(SESSAO_CHAVE)
        if not dados:
            messages.error(request, "Nenhuma prévia de importação pendente. Envie o arquivo novamente.")
            return redirect("importacao:importar")

        conteudo = base64.b64decode(dados["conteudo_b64"])
        nome = dados["nome"]
        fonte = (
            FonteDados.objects.filter(pk=dados["fonte_id"]).first()
            if dados.get("fonte_id")
            else None
        )

        importacao = services.importar(
            conteudo, nome, usuario=request.user, fonte=fonte
        )
        request.session.pop(SESSAO_CHAVE, None)
        messages.success(
            request,
            f"Importação concluída: {importacao.qtd_importados} importados, "
            f"{importacao.qtd_rejeitados} rejeitados.",
        )
        return render(
            request,
            "importacao/resultado.html",
            {"importacao": importacao, "resultado": getattr(importacao, "resultado", None)},
        )


class ImportacaoCancelarView(ImportaRequiredMixin, View):
    def post(self, request):
        request.session.pop(SESSAO_CHAVE, None)
        messages.info(request, "Prévia descartada.")
        return redirect("importacao:importar")


class ImportacaoOficialView(ImportaRequiredMixin, FormView):
    """Importa uma aba da planilha oficial INVENTARIO OFICIAL OLIMPIA (um segmento)."""

    template_name = "importacao/importar_oficial.html"
    form_class = ImportacaoOficialForm

    def form_valid(self, form):
        arquivo = form.cleaned_data["arquivo"]
        segmento = form.cleaned_data["segmento"].strip()
        try:
            registros, resumo = oficial.importar_arquivo(
                arquivo.read(), arquivo.name, segmento, usuario=self.request.user
            )
        except (ArquivoNaoSuportado, UnicodeDecodeError, Exception) as exc:
            form.add_error("arquivo", f"Não foi possível processar: {exc}")
            return self.form_invalid(form)

        messages.success(
            self.request,
            f"Planilha oficial processada ({segmento}): {resumo['criados']} criados, "
            f"{resumo['atualizados']} atualizados, {resumo['ignorados']} ignorados.",
        )
        return render(
            self.request,
            "importacao/resultado_oficial.html",
            {"segmento": segmento, "resumo": resumo, "registros": registros},
        )


class ImportacaoListView(ImportaRequiredMixin, ListView):
    model = Importacao
    template_name = "importacao/historico.html"
    context_object_name = "importacoes"
    paginate_by = 20


class ImportacaoDetailView(ImportaRequiredMixin, DetailView):
    model = Importacao
    template_name = "importacao/detalhe.html"
    context_object_name = "importacao"
