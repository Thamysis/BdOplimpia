"""Cenarios funcionais complementares aos testes por modulo.

Cada teste usa a rota publica correspondente ao caso de uso, para verificar
permissoes, persistencia e resultado observavel pelo usuario.
"""

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from acesso.models import Perfil, Usuario
from auditoria.models import AcaoAuditoria, AlteracaoInventario
from importacao.models import Importacao
from inventario.models import ItemInventario, StatusItem
from ods.models import DadoPesquisaODS, IndicadorODS, MedicaoIndicador, RegraCalculo


class CenariosFuncionaisTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = Usuario.objects.create_user("admin_cenario", password="x", perfil=Perfil.ADMINISTRADOR)
        cls.operador = Usuario.objects.create_user("operador_cenario", password="x", perfil=Perfil.OPERADOR)
        cls.gestor = Usuario.objects.create_user("gestor_cenario", password="x", perfil=Perfil.GESTOR)

    def arquivo(self, nome="itens.csv"):
        return SimpleUploadedFile(nome, b"nome,bairro\nHotel Cenario,Centro\n", content_type="text/csv")

    def test_bdp13_login_pela_interface_inicia_sessao(self):
        resposta = self.client.post(
            reverse("acesso:login"),
            {"username": "admin_cenario", "password": "x"},
        )
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.admin.pk)
        self.assertEqual(self.client.get(reverse("inventario:lista")).status_code, 200)

    def test_bdp13_admin_cria_usuario_e_desativa_acesso(self):
        self.client.force_login(self.admin)
        resposta = self.client.post(
            reverse("acesso:usuario_novo"),
            {
                "username": "novo_operador", "password1": "SenhaSegura123!",
                "password2": "SenhaSegura123!", "perfil": Perfil.OPERADOR,
                "ativo": "on",
            },
        )
        self.assertEqual(resposta.status_code, 302)
        usuario = Usuario.objects.get(username="novo_operador")
        self.assertTrue(usuario.check_password("SenhaSegura123!"))
        self.assertTrue(usuario.is_active)

        resposta = self.client.post(
            reverse("acesso:usuario_editar", args=[usuario.pk]),
            {"username": usuario.username, "perfil": Perfil.OPERADOR},
        )
        self.assertEqual(resposta.status_code, 302)
        usuario.refresh_from_db()
        self.assertFalse(usuario.ativo)
        self.assertFalse(usuario.is_active)
        self.client.logout()
        self.assertFalse(self.client.login(username="novo_operador", password="SenhaSegura123!"))

    def test_bdp13_nao_autenticado_e_redirecionado_em_rotas_protegidas(self):
        for rota in ("inventario:lista", "inventario:novo", "importacao:importar", "ods:indicador_lista"):
            with self.subTest(rota=rota):
                resposta = self.client.get(reverse(rota))
                self.assertEqual(resposta.status_code, 302)
                self.assertIn(reverse("acesso:login"), resposta.url)

    def test_bdp13_operador_nao_pode_importar_nem_confirmar(self):
        self.client.force_login(self.operador)
        for rota in ("importacao:importar", "importacao:importar_oficial", "importacao:historico"):
            with self.subTest(rota=rota):
                self.assertEqual(self.client.get(reverse(rota)).status_code, 403)
        self.assertEqual(self.client.post(reverse("importacao:confirmar")).status_code, 403)
        self.assertEqual(Importacao.objects.count(), 0)

    def test_bdp13_gestor_nao_pode_inativar_item(self):
        item = ItemInventario.objects.create(nome="Hotel protegido")
        self.client.force_login(self.gestor)
        self.assertEqual(self.client.get(reverse("inventario:novo")).status_code, 403)
        resposta = self.client.post(reverse("inventario:inativar", args=[item.pk]))
        item.refresh_from_db()
        self.assertEqual(resposta.status_code, 403)
        self.assertEqual(item.status, StatusItem.ATIVO)
        self.assertFalse(AlteracaoInventario.objects.filter(item=item).exists())

    def test_bdp03_edicao_sem_alteracao_nao_cria_historico(self):
        item = ItemInventario.objects.create(nome="Hotel estavel", bairro="Centro")
        self.client.force_login(self.operador)
        resposta = self.client.post(
            reverse("inventario:editar", args=[item.pk]),
            {"nome": "Hotel estavel", "bairro": "Centro"},
        )
        self.assertEqual(resposta.status_code, 302)
        self.assertFalse(AlteracaoInventario.objects.filter(item=item).exists())

    def test_bdp05_reativar_retorna_a_listagem_e_registra_autor(self):
        item = ItemInventario.objects.create(nome="Hotel reaberto", status=StatusItem.INATIVO)
        self.client.force_login(self.operador)
        resposta = self.client.post(reverse("inventario:reativar", args=[item.pk]))
        item.refresh_from_db()
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(item.status, StatusItem.ATIVO)
        self.assertIn(item, list(self.client.get(reverse("inventario:lista")).context["itens"]))
        registro = AlteracaoInventario.objects.get(item=item, acao=AcaoAuditoria.REATIVACAO)
        self.assertEqual(registro.usuario, self.operador)

    def test_bdp05_repetir_inativacao_nao_duplica_historico(self):
        item = ItemInventario.objects.create(nome="Hotel encerrado")
        self.client.force_login(self.operador)
        url = reverse("inventario:inativar", args=[item.pk])
        self.client.post(url)
        self.client.post(url)
        self.assertEqual(
            AlteracaoInventario.objects.filter(item=item, acao=AcaoAuditoria.INATIVACAO).count(), 1
        )

    def test_bdp01_previa_nao_grava_e_confirmacao_repetida_nao_duplica(self):
        self.client.force_login(self.admin)
        resposta = self.client.post(reverse("importacao:importar"), {"arquivo": self.arquivo()})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(ItemInventario.objects.count(), 0)
        self.assertEqual(Importacao.objects.count(), 0)
        resposta = self.client.post(reverse("importacao:confirmar"))
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(ItemInventario.objects.filter(nome="Hotel Cenario").count(), 1)
        self.assertEqual(Importacao.objects.count(), 1)
        resposta = self.client.post(reverse("importacao:confirmar"))
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(ItemInventario.objects.count(), 1)
        self.assertEqual(Importacao.objects.count(), 1)

    def test_bdp01_cancelamento_impede_confirmacao_posterior(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("importacao:importar"), {"arquivo": self.arquivo()})
        self.assertEqual(self.client.post(reverse("importacao:cancelar")).status_code, 302)
        self.assertEqual(self.client.post(reverse("importacao:confirmar")).status_code, 302)
        self.assertEqual(ItemInventario.objects.count(), 0)

    def test_bdp10_calculo_pela_interface_registra_medicao(self):
        indicador = IndicadorODS.objects.create(nome="Demanda registrada", regra_calculo=RegraCalculo.MANUAL)
        DadoPesquisaODS.objects.create(indicador=indicador, data_referencia="2026-01-01", valor=10)
        DadoPesquisaODS.objects.create(indicador=indicador, data_referencia="2026-02-01", valor=5)
        self.client.force_login(self.gestor)
        resposta = self.client.post(reverse("ods:calcular_medicao", args=[indicador.pk]))
        self.assertEqual(resposta.status_code, 302)
        medicao = MedicaoIndicador.objects.get(indicador=indicador)
        self.assertEqual(float(medicao.valor_calculado), 15.0)
        detalhe = self.client.get(reverse("ods:indicador_detalhe", args=[indicador.pk]))
        self.assertIn(medicao, list(detalhe.context["medicoes"]))

    def test_relatorio_vazio_nao_divide_por_zero(self):
        self.client.force_login(self.operador)
        resposta = self.client.get(reverse("inventario:relatorios"))
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.context["total"], 0)
        self.assertEqual(resposta.context["pct_ativos"], 0)
        self.assertEqual(resposta.context["pct_inativos"], 0)
