"""Testes do Inventário Turístico (BDP02, BDP03, BDP04, BDP05) e do modelo."""
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from acesso.models import Perfil, Usuario
from auditoria.models import AcaoAuditoria, AlteracaoInventario

from .models import (
    CampoSegmento,
    Cadastur,
    Cnae,
    Contato,
    Gerencia,
    ItemInventario,
    Participa,
    Preenchimento,
    ProfissionalTurismo,
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

    def test_alteracao_de_segmentos_e_auditada(self):
        item = ItemInventario.objects.create(nome="Hotel")
        Participa.objects.create(item=item, segmento=self.hospedagem)
        campo = CampoSegmento.objects.create(segmento=self.hospedagem, nome="Leitos")
        Preenchimento.objects.create(item=item, campo=campo, valor="20")
        resposta = self.client.post(reverse("inventario:editar", args=[item.pk]), {
            "nome": "Hotel", "segmentos": [self.alimentacao.pk],
        })
        self.assertEqual(resposta.status_code, 302)
        registro = AlteracaoInventario.objects.get(item=item, campo_alterado="segmentos")
        self.assertIn("Hospedagem", registro.valor_anterior)
        self.assertIn("Alimentação", registro.valor_novo)
        self.assertFalse(Preenchimento.objects.filter(item=item, campo=campo).exists())
        self.assertTrue(AlteracaoInventario.objects.filter(
            item=item, campo_alterado="campos de segmento"
        ).exists())


class DadosComplementaresTests(BaseInventarioTests):
    def test_edita_campos_contato_cadastur_e_vinculos_com_auditoria(self):
        item = ItemInventario.objects.create(nome="Hotel completo")
        Participa.objects.create(item=item, segmento=self.hospedagem)
        campo = CampoSegmento.objects.create(segmento=self.hospedagem, nome="Leitos", tipo_dado="numero")
        cnae = Cnae.objects.create(codigo="5510-8/01", descricao="Hotéis")
        profissional = ProfissionalTurismo.objects.create(nome="Guia Maria")
        url = reverse("inventario:dados_complementares", args=[item.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        resposta = self.client.post(url, {
            f"campo_{campo.pk}": "120", "cnaes": [cnae.pk],
            "profissionais": [profissional.pk],
            "contatos-TOTAL_FORMS": "1", "contatos-INITIAL_FORMS": "0",
            "contatos-MIN_NUM_FORMS": "0", "contatos-MAX_NUM_FORMS": "1000",
            "contatos-0-tipo": "telefone", "contatos-0-valor": "(17) 3000-0000",
            "cadastur-TOTAL_FORMS": "1", "cadastur-INITIAL_FORMS": "0",
            "cadastur-MIN_NUM_FORMS": "0", "cadastur-MAX_NUM_FORMS": "1000",
            "cadastur-0-numero": "12345", "cadastur-0-tipo": "Hotel",
        })
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(Preenchimento.objects.get(item=item, campo=campo).valor, "120")
        self.assertEqual(Contato.objects.get(item=item).valor, "(17) 3000-0000")
        self.assertEqual(Cadastur.objects.get(item=item).numero, "12345")
        self.assertTrue(item.atividades.filter(pk=cnae.pk).exists())
        self.assertTrue(item.profissionais.filter(pk=profissional.pk).exists())
        self.assertTrue(AlteracaoInventario.objects.filter(item=item, campo_alterado="contatos").exists())
        detalhe = self.client.get(reverse("inventario:detalhe", args=[item.pk]))
        self.assertContains(detalhe, "Leitos")
        self.assertContains(detalhe, "12345")


class CatalogosTests(BaseInventarioTests):
    def test_operador_cria_dados_de_apoio_para_formulario_do_item(self):
        self.assertEqual(self.client.get(reverse("inventario:catalogos")).status_code, 200)
        self.assertEqual(self.client.get(reverse("inventario:campo_novo")).status_code, 200)
        self.assertEqual(self.client.post(reverse("inventario:segmento_novo"), {
            "nome": "Eventos", "descricao": "Espaços de eventos",
        }).status_code, 302)
        segmento = Segmento.objects.get(nome="Eventos")
        self.assertEqual(self.client.post(reverse("inventario:campo_novo"), {
            "segmento": segmento.pk, "nome": "Capacidade", "tipo_dado": "numero",
        }).status_code, 302)
        self.assertEqual(self.client.post(reverse("inventario:cnae_novo"), {
            "codigo": "8230-0/01", "descricao": "Eventos",
        }).status_code, 302)
        self.assertEqual(self.client.post(reverse("inventario:profissional_novo"), {
            "nome": "Guia Ana", "cpf": "", "endereco": "Centro", "classificacao": "Guia",
        }).status_code, 302)
        self.assertTrue(CampoSegmento.objects.filter(segmento=segmento, nome="Capacidade").exists())
        self.assertTrue(Cnae.objects.filter(codigo="8230-0/01").exists())
        self.assertTrue(ProfissionalTurismo.objects.filter(nome="Guia Ana").exists())


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

    def test_paginacao_preserva_filtros(self):
        ItemInventario.objects.bulk_create(
            ItemInventario(nome=f"Hotel {numero}") for numero in range(21)
        )
        resposta = self.client.get(reverse("inventario:lista"), {"nome": "Hotel", "page": "2"})
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "?nome=Hotel&amp;page=1")
        self.assertNotContains(resposta, 'href="?page=1"')

    def test_status_inativo_funciona_sem_marcar_incluir_inativos(self):
        inativo = ItemInventario.objects.create(nome="Hotel fechado", status=StatusItem.INATIVO)
        resposta = self.client.get(reverse("inventario:lista"), {"status": StatusItem.INATIVO})
        self.assertEqual(list(resposta.context["itens"]), [inativo])


class GerenciaAcessoTests(TestCase):
    def setUp(self):
        self.operador = Usuario.objects.create_user(
            "empresa", password="x", perfil=Perfil.OPERADOR
        )
        self.admin = Usuario.objects.create_user(
            "admin-gerencia", password="x", perfil=Perfil.ADMINISTRADOR
        )

        self.item_permitido = ItemInventario.objects.create(
            nome="Hotel Permitido"
        )
        self.item_outro = ItemInventario.objects.create(
            nome="Hotel de Outra Empresa"
        )

        Gerencia.objects.create(
            usuario=self.operador,
            item=self.item_permitido,
        )

    def test_usuario_com_gerencia_lista_apenas_itens_vinculados(self):
        self.client.login(username="empresa", password="x")

        resposta = self.client.get(reverse("inventario:lista"))

        itens = list(resposta.context["itens"])
        self.assertIn(self.item_permitido, itens)
        self.assertNotIn(self.item_outro, itens)

    def test_admin_continua_vendo_todos_os_itens(self):
        self.client.login(username="admin-gerencia", password="x")

        resposta = self.client.get(reverse("inventario:lista"))

        itens = list(resposta.context["itens"])
        self.assertIn(self.item_permitido, itens)
        self.assertIn(self.item_outro, itens)

    def test_usuario_com_gerencia_nao_acessa_detalhe_de_outro_item(self):
        self.client.login(username="empresa", password="x")

        resposta = self.client.get(
            reverse("inventario:detalhe", args=[self.item_outro.pk])
        )

        self.assertEqual(resposta.status_code, 404)

    def test_usuario_com_gerencia_nao_edita_outro_item(self):
        self.client.login(username="empresa", password="x")

        resposta = self.client.get(
            reverse("inventario:editar", args=[self.item_outro.pk])
        )

        self.assertEqual(resposta.status_code, 404)

    def test_usuario_com_gerencia_nao_inativa_outro_item(self):
        self.client.login(username="empresa", password="x")

        resposta = self.client.post(
            reverse("inventario:inativar", args=[self.item_outro.pk])
        )

        self.assertEqual(resposta.status_code, 404)

        self.item_outro.refresh_from_db()
        self.assertEqual(self.item_outro.status, StatusItem.ATIVO)

    def test_usuario_com_gerencia_nao_acessa_dados_complementares_de_outro_item(self):
        self.client.login(username="empresa", password="x")

        resposta = self.client.get(
            reverse(
                "inventario:dados_complementares",
                args=[self.item_outro.pk],
            )
        )

        self.assertEqual(resposta.status_code, 404)


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

    def test_gerencia_nao_permite_usuario_item_duplicado(self):
        usuario = Usuario.objects.create_user(
            "empresa", password="x", perfil=Perfil.OPERADOR
        )
        item = ItemInventario.objects.create(nome="Hotel Gerenciado")

        Gerencia.objects.create(usuario=usuario, item=item)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Gerencia.objects.create(usuario=usuario, item=item)


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
        self.assertContains(resp, 'style="width: 66.67%"')
        self.assertContains(resp, 'style="width: 33.33%"')
        self.assertContains(resp, 'style="width: 50.00%"')

    def test_relatorios_exige_login(self):
        self.client.logout()
        resp = self.client.get(reverse("inventario:relatorios"))
        self.assertEqual(resp.status_code, 302)
