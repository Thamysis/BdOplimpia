"""Testes de autenticação e permissões por perfil (BDP13)."""
from django.test import TestCase
from django.urls import reverse

from .models import Perfil, Usuario


class AutenticacaoTests(TestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            "admin", password="senha-admin", perfil=Perfil.ADMINISTRADOR
        )
        self.operador = Usuario.objects.create_user(
            "operador", password="senha-oper", perfil=Perfil.OPERADOR
        )
        self.gestor = Usuario.objects.create_user(
            "gestor", password="senha-gestor", perfil=Perfil.GESTOR
        )

    def test_credenciais_validas_permitem_entrar(self):
        ok = self.client.login(username="admin", password="senha-admin")
        self.assertTrue(ok)

    def test_credenciais_invalidas_sao_recusadas(self):
        ok = self.client.login(username="admin", password="errada")
        self.assertFalse(ok)

    def test_logout_encerra_acesso(self):
        self.client.login(username="admin", password="senha-admin")
        self.client.get(reverse("acesso:logout"))
        # Após logout, página protegida redireciona ao login.
        resp = self.client.get(reverse("inventario:novo"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("acesso:login"), resp.url)

    def test_admin_gerencia_usuarios(self):
        self.client.login(username="admin", password="senha-admin")
        resp = self.client.get(reverse("acesso:usuario_lista"))
        self.assertEqual(resp.status_code, 200)

    def test_operador_edita_inventario_sem_gerenciar_usuarios(self):
        self.client.login(username="operador", password="senha-oper")
        # Pode acessar cadastro de item.
        self.assertEqual(self.client.get(reverse("inventario:novo")).status_code, 200)
        # Não pode gerenciar usuários.
        self.assertEqual(
            self.client.get(reverse("acesso:usuario_lista")).status_code, 403
        )

    def test_gestor_consulta_indicadores_sem_gerenciar_usuarios(self):
        self.client.login(username="gestor", password="senha-gestor")
        self.assertEqual(
            self.client.get(reverse("ods:indicador_lista")).status_code, 200
        )
        self.assertEqual(
            self.client.get(reverse("acesso:usuario_lista")).status_code, 403
        )

    def test_gestor_nao_edita_inventario(self):
        self.client.login(username="gestor", password="senha-gestor")
        self.assertEqual(self.client.get(reverse("inventario:novo")).status_code, 403)

    def test_usuario_inativo_nao_entra(self):
        Usuario.objects.create_user(
            "inativo", password="x", perfil=Perfil.OPERADOR, ativo=False
        )
        self.assertFalse(self.client.login(username="inativo", password="x"))
