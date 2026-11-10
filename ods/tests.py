"""Testes do Módulo ODS (BDP08, BDP09, BDP10, BDP12)."""
import datetime

from django.test import TestCase
from django.urls import reverse

from acesso.models import Perfil, Usuario
from inventario.models import (
    CampoSegmento,
    ItemInventario,
    Participa,
    Preenchimento,
    Segmento,
    StatusItem,
)

from .models import (
    DadoPesquisaODS,
    IndicadorODS,
    MedicaoIndicador,
    RegraCalculo,
    VinculoInventarioIndicador,
)


class BaseODSTests(TestCase):
    def setUp(self):
        self.gestor = Usuario.objects.create_user(
            "gestor", password="x", perfil=Perfil.GESTOR
        )
        self.client.login(username="gestor", password="x")


class IndicadorBDP08Tests(BaseODSTests):
    def test_cadastro_salva_nome_descricao_meta(self):
        resp = self.client.post(
            reverse("ods:indicador_novo"),
            {
                "nome": "Turismo sustentável",
                "descricao": "Itens com práticas sustentáveis",
                "meta": "80%",
                "regra_calculo": RegraCalculo.MANUAL,
            },
        )
        self.assertEqual(resp.status_code, 302)
        ind = IndicadorODS.objects.get(nome="Turismo sustentável")
        self.assertEqual(ind.descricao, "Itens com práticas sustentáveis")
        self.assertEqual(ind.meta, "80%")

    def test_cadastro_sem_nome_e_recusado(self):
        resp = self.client.post(
            reverse("ods:indicador_novo"),
            {"nome": "", "regra_calculo": RegraCalculo.MANUAL},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(IndicadorODS.objects.count(), 0)


class DadoPesquisaBDP09Tests(BaseODSTests):
    def test_registra_dados_e_aparecem_no_indicador_certo(self):
        ind_a = IndicadorODS.objects.create(nome="Indicador A")
        ind_b = IndicadorODS.objects.create(nome="Indicador B")
        for valor in (10, 20):
            self.client.post(
                reverse("ods:dado_pesquisa_novo"),
                {
                    "indicador": ind_a.pk,
                    "data_referencia": "2026-01-01",
                    "valor": valor,
                    "origem_pesquisa": "Google Forms",
                },
            )
        self.assertEqual(ind_a.dados_pesquisa.count(), 2)
        self.assertEqual(ind_b.dados_pesquisa.count(), 0)

    def test_dado_sem_indicador_e_recusado(self):
        resp = self.client.post(
            reverse("ods:dado_pesquisa_novo"),
            {"indicador": "", "data_referencia": "2026-01-01", "valor": 10},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(DadoPesquisaODS.objects.count(), 0)


class RegraCalculoBDP10Tests(BaseODSTests):
    def test_conta_itens_ativos_com_campo_sustentabilidade_sim(self):
        seg = Segmento.objects.create(nome="Hospedagem")
        campo = CampoSegmento.objects.create(segmento=seg, nome="sustentabilidade")

        ativo = ItemInventario.objects.create(nome="Hotel Verde", status=StatusItem.ATIVO)
        inativo = ItemInventario.objects.create(
            nome="Hotel Fechado", status=StatusItem.INATIVO
        )
        for item in (ativo, inativo):
            Participa.objects.create(item=item, segmento=seg)
            Preenchimento.objects.create(item=item, campo=campo, valor="Sim")

        indicador = IndicadorODS.objects.create(
            nome="Hotéis sustentáveis",
            regra_calculo=RegraCalculo.CONTAR_ITENS_CAMPO,
            regra_campo="sustentabilidade",
            regra_valor="Sim",
        )
        VinculoInventarioIndicador.objects.create(indicador=indicador, item=ativo)

        # 1 ativo + 1 inativo com o valor => resultado deve ser 1 (só ativos).
        self.assertEqual(indicador.calcular(), 1.0)

        # Recalcular reflete alteração: reativar o item inativo sobe para 2.
        inativo.status = StatusItem.ATIVO
        inativo.save()
        self.assertEqual(indicador.calcular(), 2.0)


class HistoricoBDP12Tests(BaseODSTests):
    def test_historico_ordenado_da_mais_antiga_a_mais_recente(self):
        ind = IndicadorODS.objects.create(nome="Indicador H")
        # Inseridas fora de ordem.
        MedicaoIndicador.objects.create(
            indicador=ind, periodo=datetime.date(2026, 3, 1), valor_calculado=30
        )
        MedicaoIndicador.objects.create(
            indicador=ind, periodo=datetime.date(2026, 1, 1), valor_calculado=10
        )
        MedicaoIndicador.objects.create(
            indicador=ind, periodo=datetime.date(2026, 2, 1), valor_calculado=20
        )

        resp = self.client.get(reverse("ods:indicador_detalhe", args=[ind.pk]))
        medicoes = list(resp.context["medicoes"])
        periodos = [m.periodo for m in medicoes]
        self.assertEqual(
            periodos,
            [
                datetime.date(2026, 1, 1),
                datetime.date(2026, 2, 1),
                datetime.date(2026, 3, 1),
            ],
        )
        valores = [float(m.valor_calculado) for m in medicoes]
        self.assertEqual(valores, [10.0, 20.0, 30.0])
