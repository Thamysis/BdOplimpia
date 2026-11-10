"""Testes do Inventário Turístico (BDP02, BDP03, BDP04, BDP05) e do modelo."""
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from acesso.models import Perfil, Usuario
from auditoria.models import AcaoAuditoria, AlteracaoInventario

from .models import (
    CampoSegmento,
    ItemInventario,
    Participa,
    Preenchimento,
    Segmento,
    StatusItem,
)


class BaseInventarioTests(TestCase):
    def setUp(self):
        self.operador = Usuario.objects.create_user(
            "operador", password="x", perfil=Perfil.OPERADOR
        )
        self.client.login(username="operador", password="x")
        self.hospedagem = Segmento.objects.create(nome="Hospedagem")
        self.alimentacao = Segmento.objects.create(nome="Alimentação")


class CadastroItemTests(BaseInventarioTests):
    """BDP02 — cadastrar item; valida campos obrigatórios."""

    def test_cadastro_com_obrigatorios_salva_e_encontra_por_nome(self):
        resp = self.client.post(
            reverse("inventario:novo"),
            {"nome": "Hotel Thermas", "segmentos": [self.hospedagem.pk]},
        )
        self.assertEqual(resp.status_code, 302)
        item = ItemInventario.objects.get(nome="Hotel Thermas")
        self.assertEqual(item.status, StatusItem.ATIVO)
        # Encontrável pelo nome na listagem.
        lista = self.client.get(reverse("inventario:lista"), {"nome": "Hotel Thermas"})
        self.assertContains(lista, "Hotel Thermas")

    def test_cadastro_sem_obrigatorio_e_recusado_sem_criar_registro(self):
        resp = self.client.post(reverse("inventario:novo"), {"nome": ""})
        self.assertEqual(resp.status_code, 200)  # reexibe o form com erro
        self.assertFormError(resp.context["form"], "nome", "Este campo é obrigatório.")
        self.assertEqual(ItemInventario.objects.count(), 0)


class EdicaoItemTests(BaseInventarioTests):
    """BDP03 — editar item e registrar histórico."""

    def test_edicao_atualiza_consulta_e_registra_historico(self):
        item = ItemInventario.objects.create(nome="A")
        self.client.post(
            reverse("inventario:editar", args=[item.pk]), {"nome": "B"}
        )
        item.refresh_from_db()
        self.assertEqual(item.nome, "B")

        historico = AlteracaoInventario.objects.filter(item=item, campo_alterado="nome")
        self.assertEqual(historico.count(), 1)
        h = historico.first()
        self.assertEqual(h.valor_anterior, "A")
        self.assertEqual(h.valor_novo, "B")
        self.assertEqual(h.usuario, self.operador)
        self.assertIsNotNone(h.data_hora)

    def test_edicao_mantem_demais_campos(self):
        item = ItemInventario.objects.create(nome="A", bairro="Centro")
        self.client.post(
            reverse("inventario:editar", args=[item.pk]),
            {"nome": "B", "bairro": "Centro"},
        )
        item.refresh_from_db()
        self.assertEqual(item.bairro, "Centro")


class ConsultaFiltroTests(BaseInventarioTests):
    """BDP04 — consultar e filtrar itens."""

    def setUp(self):
        super().setUp()
        self.hotel_a = ItemInventario.objects.create(nome="Hotel A")
        self.hotel_b = ItemInventario.objects.create(nome="Hotel B")
        self.rest_c = ItemInventario.objects.create(nome="Restaurante C")
        Participa.objects.create(item=self.hotel_a, segmento=self.hospedagem)
        Participa.objects.create(item=self.hotel_b, segmento=self.hospedagem)
        Participa.objects.create(item=self.rest_c, segmento=self.alimentacao)

    def test_filtro_categoria_e_nome_retorna_somente_um(self):
        resp = self.client.get(
            reverse("inventario:lista"),
            {"segmento": self.hospedagem.pk, "nome": "Hotel A"},
        )
        itens = list(resp.context["itens"])
        self.assertEqual(itens, [self.hotel_a])

    def test_sem_filtros_retorna_os_tres(self):
        resp = self.client.get(reverse("inventario:lista"))
        self.assertEqual(resp.context["itens"].count(), 3)


class InativacaoTests(BaseInventarioTests):
    """BDP05 — soft delete preservando histórico."""

    def test_inativar_some_da_listagem_padrao_mas_mantem_historico(self):
        item = ItemInventario.objects.create(nome="Antigo Hotel")
        # gera histórico prévio
        self.client.post(reverse("inventario:editar", args=[item.pk]), {"nome": "Hotel X"})
        self.client.post(reverse("inventario:inativar", args=[item.pk]))

        item.refresh_from_db()
        self.assertEqual(item.status, StatusItem.INATIVO)

        # Some da listagem padrão (apenas ativos).
        lista = self.client.get(reverse("inventario:lista"))
        self.assertNotIn(item, list(lista.context["itens"]))

        # Consulta direta mostra status inativo e preserva histórico.
        self.assertTrue(ItemInventario.objects.filter(pk=item.pk).exists())
        self.assertTrue(item.historico.exists())

        # A ação de inativação foi registrada com usuário e data/hora.
        reg = AlteracaoInventario.objects.get(item=item, acao=AcaoAuditoria.INATIVACAO)
        self.assertEqual(reg.usuario, self.operador)
        self.assertIsNotNone(reg.data_hora)

    def test_listagem_pode_incluir_inativos(self):
        item = ItemInventario.objects.create(nome="Inativo", status=StatusItem.INATIVO)
        lista = self.client.get(reverse("inventario:lista"), {"incluir_inativos": "1"})
        self.assertIn(item, list(lista.context["itens"]))


class RestricoesModeloTests(TestCase):
    """Restrições de integridade do modelo lógico."""

    def test_latitude_fora_da_faixa_viola_constraint(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ItemInventario.objects.create(nome="X", latitude=200)

    def test_preenchimento_exige_item_vinculado_ao_segmento(self):
        seg = Segmento.objects.create(nome="Eventos")
        campo = CampoSegmento.objects.create(segmento=seg, nome="Capacidade")
        item = ItemInventario.objects.create(nome="Item sem vínculo")
        preench = Preenchimento(item=item, campo=campo, valor="100")
        with self.assertRaises(ValidationError):
            preench.clean()

    def test_preenchimento_valido_quando_item_vinculado(self):
        seg = Segmento.objects.create(nome="Eventos")
        campo = CampoSegmento.objects.create(segmento=seg, nome="Capacidade")
        item = ItemInventario.objects.create(nome="Centro de Eventos")
        Participa.objects.create(item=item, segmento=seg)
        preench = Preenchimento(item=item, campo=campo, valor="100")
        preench.clean()  # não deve levantar


class RelatoriosTests(BaseInventarioTests):
    """Relatórios visuais do Inventário."""

    def test_relatorios_agrega_por_status_e_segmento(self):
        a = ItemInventario.objects.create(nome="Hotel A")
        b = ItemInventario.objects.create(nome="Hotel B")
        c = ItemInventario.objects.create(nome="Rest C", status=StatusItem.INATIVO)
        Participa.objects.create(item=a, segmento=self.hospedagem)
        Participa.objects.create(item=b, segmento=self.hospedagem)
        Participa.objects.create(item=c, segmento=self.alimentacao)

        resp = self.client.get(reverse("inventario:relatorios"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["total"], 3)
        self.assertEqual(resp.context["ativos"], 2)
        self.assertEqual(resp.context["inativos"], 1)

        por_seg = {s.nome: s for s in resp.context["por_segmento"]}
        self.assertEqual(por_seg["Hospedagem"].total, 2)
        self.assertEqual(por_seg["Hospedagem"].ativos, 2)
        self.assertEqual(por_seg["Alimentação"].total, 1)
        self.assertEqual(por_seg["Alimentação"].ativos, 0)

    def test_relatorios_exige_login(self):
        self.client.logout()
        resp = self.client.get(reverse("inventario:relatorios"))
        self.assertEqual(resp.status_code, 302)
