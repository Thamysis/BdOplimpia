"""Testes das restrições XOR de Contato e Cadastur."""
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import Cadastur, Contato, ItemInventario, ProfissionalTurismo


class ContatoCadasturXorTests(TestCase):
    def setUp(self):
        self.item = ItemInventario.objects.create(nome="Hotel")
        self.prof = ProfissionalTurismo.objects.create(nome="Guia João")

    def test_contato_com_ambos_e_invalido_no_clean(self):
        c = Contato(item=self.item, profissional=self.prof, tipo="tel", valor="123")
        with self.assertRaises(ValidationError):
            c.clean()

    def test_contato_sem_nenhum_e_invalido_no_clean(self):
        c = Contato(tipo="tel", valor="123")
        with self.assertRaises(ValidationError):
            c.clean()

    def test_contato_com_ambos_viola_constraint_no_banco(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Contato.objects.create(
                    item=self.item, profissional=self.prof, tipo="tel", valor="1"
                )

    def test_contato_apenas_item_valido(self):
        c = Contato(item=self.item, tipo="tel", valor="123")
        c.clean()
        c.save()
        self.assertEqual(Contato.objects.count(), 1)

    def test_cadastur_apenas_profissional_valido(self):
        c = Cadastur(profissional=self.prof, numero="999")
        c.clean()
        c.save()
        self.assertEqual(Cadastur.objects.count(), 1)
