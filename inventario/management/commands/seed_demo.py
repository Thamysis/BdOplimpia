"""Popula a base com dados de demonstração para o OTO.

Uso: python manage.py seed_demo
Cria usuários de cada perfil (senha: demo12345), segmentos, itens de exemplo e
um indicador ODS. Idempotente: não duplica registros já existentes.
"""
from django.core.management.base import BaseCommand

from acesso.models import Perfil, Usuario
from inventario.models import ItemInventario, Participa, Segmento
from ods.models import IndicadorODS, RegraCalculo


class Command(BaseCommand):
    help = "Cria dados de demonstração do OTO."

    def handle(self, *args, **options):
        senha = "demo12345"
        contas = [
            ("admin_oto", Perfil.ADMINISTRADOR, "Administrador OTO"),
            ("operador_oto", Perfil.OPERADOR, "Operador OTO"),
            ("gestor_oto", Perfil.GESTOR, "Gestor OTO"),
        ]
        for username, perfil, nome in contas:
            user, criado = Usuario.objects.get_or_create(
                username=username,
                defaults={"perfil": perfil, "first_name": nome, "ativo": True},
            )
            if criado:
                user.set_password(senha)
                if perfil == Perfil.ADMINISTRADOR:
                    user.is_staff = True
                    user.is_superuser = True
                user.save()
                self.stdout.write(f"Usuário criado: {username} / {senha}")

        # Segmentos reais do Inventário Oficial de Olímpia (aba de controle da
        # planilha oficial INVENTARIO OFICIAL OLIMPIA).
        nomes_segmentos = [
            "Agências e Operadoras de Turismo",
            "Artesanato e Comércio Diferenciado",
            "Atrativos/Lazer/Entretenimento",
            "Casas de Temporada",
            "Educação",
            "Espaço para Eventos",
            "Eventos Programados",
            "Guias de Turismo",
            "Locadora de Veículos e Transporte Turístico",
            "Manifestações Culturais",
            "Meios de Hospedagem",
            "Meios A&B",
            "Organizadores/Serviços para Eventos",
            "Postos de Combustíveis",
            "Serviços de Saúde",
            "Serviços de Segurança",
            "Táxi, Mototáxi e Aplicativo",
            "Outros",
        ]
        segmentos = {}
        for nome in nomes_segmentos:
            seg, _ = Segmento.objects.get_or_create(nome=nome)
            segmentos[nome] = seg

        hospedagem = segmentos["Meios de Hospedagem"]
        alimentacao = segmentos["Meios A&B"]
        atrativos = segmentos["Atrativos/Lazer/Entretenimento"]

        exemplos = [
            ("Hotel Thermas", hospedagem, "Centro"),
            ("Pousada das Águas", hospedagem, "Jardim"),
            ("Restaurante Sabor de Olímpia", alimentacao, "Centro"),
            ("Parque Aquático", atrativos, "Rodovia"),
        ]
        for nome, seg, bairro in exemplos:
            item, criado = ItemInventario.objects.get_or_create(
                nome=nome, defaults={"bairro": bairro}
            )
            Participa.objects.get_or_create(item=item, segmento=seg)
            if criado:
                self.stdout.write(f"Item criado: {nome}")

        IndicadorODS.objects.get_or_create(
            nome="Estabelecimentos com práticas sustentáveis",
            defaults={
                "descricao": "Conta itens ativos com o campo sustentabilidade = Sim.",
                "meta": "50 estabelecimentos",
                "regra_calculo": RegraCalculo.CONTAR_ITENS_CAMPO,
                "regra_campo": "sustentabilidade",
                "regra_valor": "Sim",
            },
        )
        self.stdout.write(self.style.SUCCESS("Dados de demonstração prontos."))
