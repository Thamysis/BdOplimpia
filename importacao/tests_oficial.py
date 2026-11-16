"""Testes do importador do formato oficial (INVENTARIO OFICIAL OLIMPIA)."""
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from .models import Importacao, InconsistenciaImportacao
from auditoria.models import AlteracaoInventario

from inventario.models import (
    Cadastur,
    CampoSegmento,
    Contato,
    ItemInventario,
    Participa,
    Preenchimento,
    Segmento,
)

from . import oficial

# Matriz que reproduz o layout real de uma aba de categoria:
# linha 0 = banner, linha 1 = "última atualização", linha 2 = grupos mesclados,
# linha 3 = cabeçalho real, linhas 4+ = dados.
MATRIZ = [
    ["INVENTÁRIO MEIOS DE HOSPEDAGEM", "", "", "", "", "", "", "", ""],
    ["ÚLTIMA ATUALIZAÇÃO:", "", "", "", "", "", "", "", ""],
    ["", "", "DADOS MH", "", "", "", "", "", "GERAL"],
    [
        "QTD", "NOME FANTASIA", "RAZÃO SOCIAL", "CNPJ", "ENDEREÇO", "BAIRRO",
        "COORDENADAS GEOGRÁFICAS", "LEITOS", "TELEFONE COMERCIAL",
    ],
    [
        "1", "Hotel Thermas", "Thermas Ltda", "12345678000199", "Rua A, 100",
        "Centro", "-21,73, -48,91", "120", "(17) 3279-0000",
    ],
    [
        "2", "Pousada das Águas", "Águas ME", "98765432000111", "Rua B, 200",
        "Jardim", "-21,74 -48,92", "40", "(17) 3279-1111",
    ],
    ["", "", "", "", "", "", "", "", ""],  # linha vazia -> ignorada
]


class InterpretadorOficialTests(TestCase):
    def test_detecta_linha_de_cabecalho(self):
        idx = oficial.detectar_linha_cabecalho(MATRIZ)
        self.assertEqual(idx, 3)

    def test_interpreta_itens_base_contato_coordenadas_e_campos(self):
        registros = oficial.interpretar(MATRIZ, "Meios de Hospedagem")
        self.assertEqual(len(registros), 2)

        r = registros[0]
        self.assertEqual(r.base["nome"], "Hotel Thermas")
        self.assertEqual(r.base["razao_social"], "Thermas Ltda")
        self.assertEqual(r.base["documento"], "12345678000199")
        self.assertEqual(r.base["tipo_documento"], "CNPJ")
        self.assertEqual(r.base["bairro"], "Centro")
        self.assertAlmostEqual(r.base["latitude"], -21.73, places=2)
        self.assertAlmostEqual(r.base["longitude"], -48.91, places=2)
        # LEITOS vira campo de segmento; telefone vira contato.
        self.assertEqual(r.campos_segmento.get("leitos"), "120")
        self.assertIn(("telefone", "(17) 3279-0000"), r.contatos)


class PersistenciaOficialTests(TestCase):
    def test_persistir_cria_itens_vinculos_campos_e_contatos(self):
        registros = oficial.interpretar(MATRIZ, "Meios de Hospedagem")
        resumo = oficial.persistir(registros, "Meios de Hospedagem")

        self.assertEqual(resumo["criados"], 2)
        self.assertEqual(ItemInventario.objects.count(), 2)

        seg = Segmento.objects.get(nome="Meios de Hospedagem")
        hotel = ItemInventario.objects.get(nome="Hotel Thermas")

        # Vínculo com o segmento.
        self.assertTrue(Participa.objects.filter(item=hotel, segmento=seg).exists())
        # Campo específico "leitos" criado e preenchido.
        campo = CampoSegmento.objects.get(segmento=seg, nome="leitos")
        self.assertEqual(
            Preenchimento.objects.get(item=hotel, campo=campo).valor, "120"
        )
        # Contato telefônico.
        self.assertTrue(Contato.objects.filter(item=hotel, tipo="telefone").exists())
        # Coordenadas gravadas no item.
        self.assertAlmostEqual(float(hotel.latitude), -21.73, places=2)

    def test_persistir_e_idempotente(self):
        registros = oficial.interpretar(MATRIZ, "Meios de Hospedagem")
        oficial.persistir(registros, "Meios de Hospedagem")
        resumo2 = oficial.persistir(registros, "Meios de Hospedagem")
        self.assertEqual(resumo2["criados"], 0)
        self.assertEqual(ItemInventario.objects.count(), 2)

    def test_atualizacao_oficial_registra_campos_e_vinculos_no_historico(self):
        item = ItemInventario.objects.create(nome="Hotel Thermas")
        registros = oficial.interpretar(MATRIZ, "Meios de Hospedagem")[:1]
        resumo = oficial.persistir(registros, "Meios de Hospedagem")
        self.assertEqual(resumo["atualizados"], 1)
        item.refresh_from_db()
        self.assertEqual(item.bairro, "Centro")
        self.assertTrue(AlteracaoInventario.objects.filter(item=item, campo_alterado="bairro").exists())
        self.assertTrue(AlteracaoInventario.objects.filter(item=item, campo_alterado="segmentos").exists())


class LinhasDeResumoTests(TestCase):
    def test_classificacoes_e_totais_nao_viram_estabelecimentos(self):
        matriz = [
            ["INVENTÁRIO"],
            ["QTD", "NOME FANTASIA", "ENDEREÇO", "CLASSIFICAÇÃO", "QTDE"],
            ["", "BAR E LANCHONETE", "", "", "0"],
            ["", "", "", "TOTAL DE EMPRESAS", "0"],
            ["1", "Hotel válido", "Rua A", "", ""],
        ]
        previa = oficial.PreviaOficial()
        registros = oficial.interpretar(matriz, "Hospedagem", previa.rejeitadas)
        self.assertEqual([r.base["nome"] for r in registros], ["Hotel válido"])
        self.assertEqual(previa.rejeitadas, [])


class FiltroLinhasTotalTests(TestCase):
    """Linhas agregadas (TOTAL / TOTAIS DE…) não viram itens."""

    MATRIZ = [
        ["INVENTÁRIO MEIOS DE HOSPEDAGEM"],
        ["ÚLTIMA ATUALIZAÇÃO:"],
        [],
        ["QTD", "NOME FANTASIA", "RAZÃO SOCIAL", "ENDEREÇO", "BAIRRO"],
        ["0", "TOTAL", "", "", ""],
        ["", "TOTAIS DE MEIOS DE HOSPEDAGENS", "", "", ""],
        ["1", "Hotel Válido", "Hotel Válido Ltda", "Rua A", "Centro"],
    ]

    def test_ignora_linhas_de_total(self):
        regs = oficial.interpretar(self.MATRIZ, "Meios de Hospedagem")
        nomes = [r.base.get("nome") for r in regs]
        self.assertEqual(nomes, ["Hotel Válido"])

    def test_persistir_so_grava_item_valido(self):
        regs = oficial.interpretar(self.MATRIZ, "Meios de Hospedagem")
        resumo = oficial.persistir(regs, "Meios de Hospedagem")
        self.assertEqual(resumo["criados"], 1)
        self.assertEqual(ItemInventario.objects.count(), 1)


class ImportacaoOficialViewTests(TestCase):
    """Fluxo via view: upload de aba oficial grava itens do segmento."""

    def setUp(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from acesso.models import Perfil, Usuario

        self.admin = Usuario.objects.create_user(
            "admin", password="x", perfil=Perfil.ADMINISTRADOR
        )
        self.client.login(username="admin", password="x")
        # CSV com banner + cabeçalho + 1 item + 1 total.
        csv = (
            "INVENTÁRIO MEIOS DE HOSPEDAGEM,,,,\r\n"
            "ÚLTIMA ATUALIZAÇÃO:,,,,\r\n"
            ",,,,\r\n"
            "QTD,NOME FANTASIA,RAZÃO SOCIAL,ENDEREÇO,BAIRRO\r\n"
            "0,TOTAL,,,\r\n"
            "1,Hotel Central,Central Ltda,Rua A 10,Centro\r\n"
        ).encode("utf-8")
        self.arquivo = SimpleUploadedFile("mh.csv", csv, content_type="text/csv")

    def test_importa_aba_oficial(self):
        resp = self.client.post(
            reverse("importacao:importar_oficial"),
            {"segmento": "Meios de Hospedagem", "arquivo": self.arquivo},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "importacao/previa_oficial.html")
        self.assertEqual(ItemInventario.objects.count(), 0)
        resp = self.client.post(reverse("importacao:confirmar_oficial"))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "importacao/resultado_oficial.html")
        self.assertEqual(ItemInventario.objects.filter(nome="Hotel Central").count(), 1)
        self.assertEqual(ItemInventario.objects.filter(nome="TOTAL").count(), 0)
        self.assertTrue(
            Participa.objects.filter(
                item__nome="Hotel Central", segmento__nome="Meios de Hospedagem"
            ).exists()
        )
        self.assertEqual(Importacao.objects.get().qtd_importados, 1)

    def test_planilha_com_duas_abas_gera_previa_e_registra_rejeicoes(self):
        from io import BytesIO
        from openpyxl import Workbook

        wb = Workbook()
        controle = wb.active
        controle.title = "CONTROLE"
        controle.append(["Controle da planilha"])
        for titulo, nome in (("HOSPEDAGEM", "Hotel A"), ("ALIMENTAÇÃO", "Restaurante B")):
            ws = wb.create_sheet(titulo)
            ws.append(["INVENTÁRIO"])
            ws.append(["QTD", "NOME FANTASIA", "ENDEREÇO"])
            ws.append([1, nome, "Rua A"])
        ws.append([2, "Restaurante B", "Rua B"])
        ws.append([3, "", "Rua sem nome"])
        conteudo = BytesIO()
        wb.save(conteudo)
        arquivo = SimpleUploadedFile("inventario.xlsx", conteudo.getvalue())

        resp = self.client.post(reverse("importacao:importar_oficial"), {"arquivo": arquivo})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["previa"].abas, ["HOSPEDAGEM", "ALIMENTAÇÃO"])
        self.assertEqual(resp.context["previa"].total_lidos, 4)
        self.assertEqual(len(resp.context["previa"].rejeitadas), 2)
        self.assertEqual(ItemInventario.objects.count(), 0)
        self.client.post(reverse("importacao:confirmar_oficial"))
        self.assertEqual(ItemInventario.objects.count(), 2)
        self.assertEqual(Importacao.objects.get().qtd_rejeitados, 2)
        self.assertEqual(InconsistenciaImportacao.objects.count(), 2)

    def test_cancelar_previa_oficial_nao_grava(self):
        self.client.post(reverse("importacao:importar_oficial"), {
            "segmento": "Meios de Hospedagem", "arquivo": self.arquivo,
        })
        self.assertEqual(self.client.post(reverse("importacao:cancelar_oficial")).status_code, 302)
        self.assertEqual(self.client.post(reverse("importacao:confirmar_oficial")).status_code, 302)
        self.assertEqual(ItemInventario.objects.count(), 0)
