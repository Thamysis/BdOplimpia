from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse


class HealthEndpointTests(SimpleTestCase):
    def test_health_endpoint_responds(self):
        response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})


class CreditosViewTests(TestCase):
    def test_creditos_exige_autenticacao(self):
        response = self.client.get(reverse("creditos"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("acesso:login"), response.url)

    def test_creditos_exibe_equipe_curso_instituicao_ano(self):
        Usuario = get_user_model()
        user = Usuario.objects.create_user(username="tester", password="x")
        self.client.force_login(user)
        response = self.client.get(reverse("creditos"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "creditos.html")
        self.assertContains(response, "Enzo Vasconcellos Pagotto")
        self.assertContains(response, "Thamyres Santos Silva")
        self.assertContains(response, "Bacharelado em Sistemas de Informação")
        self.assertContains(response, "ICMC")
        self.assertContains(response, "2026")

