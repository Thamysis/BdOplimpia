"""Testes de importação e validação (BDP01 e BDP11)."""
from django.test import TestCase

from inventario.models import ItemInventario

from . import services
from .models import Importacao, InconsistenciaImportacao, StatusImportacao, TipoInconsistencia

# Arquivo de exemplo: 2 válidos, 1 duplicado (de "Hotel A"), 1 sem obrigatório (nome vazio).
CSV_EXEMPLO = (
    "nome,bairro\n"
    "Hotel A,Centro\n"
    "Hotel B,Jardim\n"
    "Hotel A,Centro\n"
    ",Sem Nome\n"
).encode("utf-8")


class ValidacaoBDP11Tests(TestCase):
    """BDP11 — valida integridade e resume divergências, sem gravar."""

    def test_resumo_4_verificados_2_validos_2_inconsistencias(self):
        imp = services.validar(CSV_EXEMPLO, "inventario.csv")
        self.assertEqual(imp.qtd_registros, 4)
        self.assertEqual(imp.qtd_registros - imp.qtd_rejeitados, 2)  # válidos
        self.assertEqual(imp.qtd_rejeitados, 2)
        # Nenhum registro inválido é incorporado à base (validação não grava).
        self.assertEqual(ItemInventario.objects.count(), 0)

    def test_cada_inconsistencia_tem_linha_tipo_e_motivo(self):
        imp = services.validar(CSV_EXEMPLO, "inventario.csv")
        incs = list(imp.inconsistencias.all())
        self.assertEqual(len(incs), 2)
        tipos = {i.tipo for i in incs}
        self.assertEqual(
            tipos, {TipoInconsistencia.DUPLICIDADE, TipoInconsistencia.CAMPO_OBRIGATORIO}
        )
        for inc in incs:
            self.assertTrue(inc.referencia_origem)  # linha
            self.assertTrue(inc.tipo)  # tipo
            self.assertTrue(inc.descricao)  # motivo

    def test_status_com_inconsistencias(self):
        imp = services.validar(CSV_EXEMPLO, "inventario.csv")
        self.assertEqual(imp.status, StatusImportacao.COM_INCONSISTENCIAS)


class ImportacaoBDP01Tests(TestCase):
    """BDP01 — importa válidos uma única vez e aponta rejeições."""

    def test_importa_2_rejeita_2_e_resumo(self):
        imp = services.importar(CSV_EXEMPLO, "inventario.csv")
        self.assertEqual(imp.qtd_registros, 4)
        self.assertEqual(imp.qtd_importados, 2)
        self.assertEqual(imp.qtd_rejeitados, 2)

    def test_validos_gravados_uma_unica_vez(self):
        services.importar(CSV_EXEMPLO, "inventario.csv")
        self.assertEqual(ItemInventario.objects.count(), 2)
        self.assertEqual(ItemInventario.objects.filter(nome="Hotel A").count(), 1)
        self.assertEqual(ItemInventario.objects.filter(nome="Hotel B").count(), 1)

    def test_rejeicoes_identificam_linha_e_motivo(self):
        imp = services.importar(CSV_EXEMPLO, "inventario.csv")
        incs = list(imp.inconsistencias.all())
        self.assertEqual(len(incs), 2)
        motivos = " ".join(i.descricao.lower() for i in incs)
        self.assertIn("duplicado", motivos)
        self.assertIn("obrigatório", motivos)

    def test_duplicidade_contra_base_existente(self):
        ItemInventario.objects.create(nome="Hotel A")
        csv = "nome\nHotel A\nHotel Novo\n".encode("utf-8")
        imp = services.importar(csv, "novo.csv")
        self.assertEqual(imp.qtd_importados, 1)  # só Hotel Novo
        self.assertEqual(imp.qtd_rejeitados, 1)  # Hotel A duplicado
        self.assertEqual(ItemInventario.objects.filter(nome="Hotel A").count(), 1)

    def test_coordenada_invalida_e_rejeitada(self):
        csv = "nome,latitude\nHotel X,200\nHotel Y,-22.8\n".encode("utf-8")
        imp = services.importar(csv, "coords.csv")
        self.assertEqual(imp.qtd_importados, 1)
        self.assertEqual(imp.qtd_rejeitados, 1)

    def test_separador_ponto_e_virgula(self):
        csv = "nome;bairro\nHotel Z;Centro\n".encode("utf-8")
        imp = services.importar(csv, "pv.csv")
        self.assertEqual(imp.qtd_importados, 1)


class ImportacaoXLSXTests(TestCase):
    """Importação a partir de planilha XLSX (openpyxl)."""

    def _montar_xlsx(self):
        import io

        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.append(["nome", "bairro"])
        ws.append(["Hotel XLSX A", "Centro"])
        ws.append(["Hotel XLSX B", "Jardim"])
        ws.append(["Hotel XLSX A", "Centro"])  # duplicado
        buffer = io.BytesIO()
        wb.save(buffer)
        return buffer.getvalue()

    def test_importa_xlsx_classifica_corretamente(self):
        conteudo = self._montar_xlsx()
        imp = services.importar(conteudo, "inventario.xlsx")
        self.assertEqual(imp.qtd_registros, 3)
        self.assertEqual(imp.qtd_importados, 2)
        self.assertEqual(imp.qtd_rejeitados, 1)
        self.assertEqual(ItemInventario.objects.filter(nome="Hotel XLSX A").count(), 1)


class PreviaImportacaoFluxoTests(TestCase):
    """Fluxo de prévia -> confirmação via views (BDP01)."""

    def setUp(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from acesso.models import Perfil, Usuario

        self.admin = Usuario.objects.create_user(
            "admin", password="x", perfil=Perfil.ADMINISTRADOR
        )
        self.client.login(username="admin", password="x")
        self.arquivo = SimpleUploadedFile(
            "inventario.csv", CSV_EXEMPLO, content_type="text/csv"
        )

    def _reverse(self, nome):
        from django.urls import reverse

        return reverse(nome)

    def test_upload_gera_previa_sem_gravar(self):
        resp = self.client.post(
            self._reverse("importacao:importar"), {"arquivo": self.arquivo}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "importacao/previa.html")
        resultado = resp.context["resultado"]
        self.assertEqual(resultado.total_lidos, 4)
        self.assertEqual(resultado.total_aceitas, 2)
        self.assertEqual(resultado.total_rejeitadas, 2)
        # Nada gravado ainda na prévia.
        self.assertEqual(ItemInventario.objects.count(), 0)
        self.assertEqual(Importacao.objects.count(), 0)

    def test_confirmar_grava_itens_aceitos(self):
        self.client.post(self._reverse("importacao:importar"), {"arquivo": self.arquivo})
        resp = self.client.post(self._reverse("importacao:confirmar"))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "importacao/resultado.html")
        self.assertEqual(ItemInventario.objects.count(), 2)
        imp = Importacao.objects.get()
        self.assertEqual(imp.qtd_importados, 2)
        self.assertEqual(imp.qtd_rejeitados, 2)

    def test_confirmar_sem_previa_redireciona(self):
        resp = self.client.post(self._reverse("importacao:confirmar"))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(ItemInventario.objects.count(), 0)

    def test_cancelar_descarta_previa(self):
        self.client.post(self._reverse("importacao:importar"), {"arquivo": self.arquivo})
        self.client.post(self._reverse("importacao:cancelar"))
        # Após cancelar, confirmar não grava nada.
        resp = self.client.post(self._reverse("importacao:confirmar"))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(ItemInventario.objects.count(), 0)
