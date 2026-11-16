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
SESSAO_OFICIAL_CHAVE = "importacao_oficial_preview"


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
    """Gera prévia de todas as abas reconhecidas da planilha oficial."""

    template_name = "importacao/importar_oficial.html"
    form_class = ImportacaoOficialForm

    def form_valid(self, form):
        arquivo = form.cleaned_data["arquivo"]
        segmento = form.cleaned_data["segmento"].strip()
        conteudo = arquivo.read()
        try:
            previa = oficial.preparar(conteudo, arquivo.name, segmento)
        except (ArquivoNaoSuportado, UnicodeDecodeError, ValueError, Exception) as exc:
            form.add_error("arquivo", f"Não foi possível processar: {exc}")
            return self.form_invalid(form)
        self.request.session[SESSAO_OFICIAL_CHAVE] = {
            "conteudo_b64": base64.b64encode(conteudo).decode("ascii"),
            "nome": arquivo.name, "segmento": segmento,
        }
        return render(
            self.request,
            "importacao/previa_oficial.html",
            {"previa": previa, "nome_arquivo": arquivo.name},
        )


class ImportacaoOficialConfirmarView(ImportaRequiredMixin, View):
    def post(self, request):
        dados = request.session.get(SESSAO_OFICIAL_CHAVE)
        if not dados:
            messages.error(request, "Nenhuma prévia oficial pendente.")
            return redirect("importacao:importar_oficial")
        conteudo = base64.b64decode(dados["conteudo_b64"])
        previa = oficial.preparar(conteudo, dados["nome"], dados["segmento"])
        carga, resumo = oficial.confirmar_previa(previa, dados["nome"], usuario=request.user)
        request.session.pop(SESSAO_OFICIAL_CHAVE, None)
        messages.success(request, "Importação oficial concluída.")
        return render(request, "importacao/resultado_oficial.html", {
            "segmento": ", ".join(previa.abas), "resumo": resumo,
            "registros": [registro for _, registro in previa.aceitas],
            "importacao": carga,
        })


class ImportacaoOficialCancelarView(ImportaRequiredMixin, View):
    def post(self, request):
        request.session.pop(SESSAO_OFICIAL_CHAVE, None)
        messages.info(request, "Prévia oficial descartada.")
        return redirect("importacao:importar_oficial")


class ImportacaoListView(ImportaRequiredMixin, ListView):
    model = Importacao
    template_name = "importacao/historico.html"
    context_object_name = "importacoes"
    paginate_by = 20


class ImportacaoDetailView(ImportaRequiredMixin, DetailView):
    model = Importacao
    template_name = "importacao/detalhe.html"
    context_object_name = "importacao"
