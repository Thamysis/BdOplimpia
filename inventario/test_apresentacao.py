"""A carga de apresentação deve ser segura para repetir e coerente nas telas."""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from inventario.models import Cadastur, Contato, ItemInventario, StatusItem
from ods.models import DadoPesquisaODS, IndicadorODS, MedicaoIndicador


class DadosApresentacaoTests(TestCase):
    def test_carga_ficticia_e_repetivel_com_historico_e_ods(self):
        saida = StringIO()
        call_command("seed_apresentacao", stdout=saida)
        call_command("seed_apresentacao", stdout=saida)

        self.assertEqual(ItemInventario.objects.filter(nome__startswith="[Demo]").count(), 12)
        self.assertEqual(ItemInventario.objects.filter(
            nome__startswith="[Demo]", status=StatusItem.INATIVO,
        ).count(), 2)
        hotel = ItemInventario.objects.get(nome="[Demo] Hotel Lago Azul")
        self.assertTrue(hotel.historico.filter(campo_alterado="bairro").exists())
        self.assertEqual(Contato.objects.filter(item=hotel).count(), 1)
        self.assertEqual(Cadastur.objects.filter(item=hotel).count(), 1)
        indicador = IndicadorODS.objects.get(nome="[Demo] Estabelecimentos com práticas sustentáveis")
        self.assertEqual(indicador.calcular(), 6)
        pesquisa = IndicadorODS.objects.get(nome="[Demo] Atendimentos em ações de turismo")
        self.assertEqual(pesquisa.calcular(), 180)
        self.assertEqual(DadoPesquisaODS.objects.filter(indicador=pesquisa).count(), 3)
        self.assertEqual(MedicaoIndicador.objects.filter(indicador=pesquisa).count(), 3)
