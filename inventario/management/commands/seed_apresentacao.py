"""Cria um conjunto fictício e repetível para demonstrar as telas do OTO."""

from datetime import date

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from acesso.models import Usuario
from auditoria.services import registrar_criacao, registrar_edicao, snapshot
from inventario.models import (
    Cadastur, CampoSegmento, Cnae, Contato, ItemInventario, Participa,
    PossuiAtividade, Preenchimento, ProfissionalTurismo, Segmento, StatusItem,
    VinculoProfissionalItem,
)
from ods.models import (
    DadoPesquisaODS, IndicadorODS, MedicaoIndicador, ODS, ODSIndicador,
    RegraCalculo, VinculoInventarioIndicador,
)


class Command(BaseCommand):
    help = "Adiciona dados fictícios para apresentar Inventário, relatórios e ODS."

    @transaction.atomic
    def handle(self, *args, **options):
        call_command("seed_demo", stdout=self.stdout)
        admin = Usuario.objects.get(username="admin_oto")
        segmentos = {s.nome: s for s in Segmento.objects.all()}

        # Nomes e registros são intencionalmente fictícios; nunca representam
        # estabelecimentos cadastrados na planilha oficial.
        exemplos = [
            ("Hotel Lago Azul", "Meios de Hospedagem", "Centro", "Sim", StatusItem.ATIVO),
            ("Pousada Ipê", "Meios de Hospedagem", "Jardim", "Não", StatusItem.ATIVO),
            ("Chalés Primavera", "Meios de Hospedagem", "Rural", "Sim", StatusItem.ATIVO),
            ("Restaurante Estação", "Meios A&B", "Centro", "Sim", StatusItem.ATIVO),
            ("Café das Águas", "Meios A&B", "Jardim", "Não", StatusItem.ATIVO),
            ("Parque Verde", "Atrativos/Lazer/Entretenimento", "Rural", "Sim", StatusItem.ATIVO),
            ("Museu das Memórias", "Atrativos/Lazer/Entretenimento", "Centro", "Sim", StatusItem.ATIVO),
            ("Agência Caminhos", "Agências e Operadoras de Turismo", "Centro", "Não", StatusItem.ATIVO),
            ("Ateliê das Flores", "Artesanato e Comércio Diferenciado", "Jardim", "Sim", StatusItem.ATIVO),
            ("Espaço Horizonte", "Espaço para Eventos", "Centro", "Não", StatusItem.ATIVO),
            ("Pousada Antiga", "Meios de Hospedagem", "Centro", "Não", StatusItem.INATIVO),
            ("Café da Praça", "Meios A&B", "Centro", "Sim", StatusItem.INATIVO),
        ]
        itens = []
        novos = 0
        for nome, segmento_nome, bairro, sustentavel, status in exemplos:
            segmento = segmentos[segmento_nome]
            item, criado = ItemInventario.objects.get_or_create(
                nome=f"[Demo] {nome}",
                defaults={
                    "bairro": "A definir" if nome == "Hotel Lago Azul" else bairro,
                    "endereco": "Endereço fictício para apresentação",
                    "status": status,
                },
            )
            if criado:
                novos += 1
                registrar_criacao(item, usuario=admin)
            Participa.objects.get_or_create(item=item, segmento=segmento)
            campo, _ = CampoSegmento.objects.get_or_create(
                segmento=segmento, nome="Sustentabilidade",
                defaults={"tipo_dado": CampoSegmento.TipoDado.BOOLEANO},
            )
            Preenchimento.objects.get_or_create(
                item=item, campo=campo, defaults={"valor": sustentavel},
            )
            if criado and nome == "Hotel Lago Azul":
                anterior = snapshot(item)
                item.bairro = bairro
                item.save(update_fields=["bairro", "atualizado_em"])
                registrar_edicao(item, anterior, usuario=admin)
            itens.append(item)

        hotel = itens[0]
        restaurante = itens[3]
        Contato.objects.get_or_create(
            item=hotel, tipo="e-mail", valor="hotel.demo@exemplo.invalid",
            defaults={"finalidade": "Reservas"},
        )
        Contato.objects.get_or_create(
            item=restaurante, tipo="e-mail", valor="restaurante.demo@exemplo.invalid",
            defaults={"finalidade": "Informações"},
        )
        Cadastur.objects.get_or_create(
            item=hotel, numero="DEMO-CADASTUR-001",
            defaults={"tipo": "Hospedagem", "situacao": "Registro fictício"},
        )
        cnae, _ = Cnae.objects.get_or_create(
            codigo="5510-8/01", defaults={"descricao": "Hotéis"},
        )
        PossuiAtividade.objects.get_or_create(item=hotel, cnae=cnae)
        guia, _ = ProfissionalTurismo.objects.get_or_create(
            nome="[Demo] Guia de Turismo", defaults={"classificacao": "Guia"},
        )
        VinculoProfissionalItem.objects.get_or_create(item=itens[5], profissional=guia)

        ods_12, _ = ODS.objects.get_or_create(
            numero=12, nome="Consumo e produção responsáveis",
        )
        ods_8, _ = ODS.objects.get_or_create(
            numero=8, nome="Trabalho decente e crescimento econômico",
        )
        sustentaveis, _ = IndicadorODS.objects.get_or_create(
            nome="[Demo] Estabelecimentos com práticas sustentáveis",
            defaults={
                "descricao": "Conta itens ativos de demonstração com Sustentabilidade = Sim.",
                "meta": "10 estabelecimentos (exemplo)",
                "regra_calculo": RegraCalculo.CONTAR_ITENS_CAMPO,
                "regra_campo": "Sustentabilidade",
                "regra_valor": "Sim",
                "regra_descricao": "Somente itens vinculados e ativos entram na contagem.",
            },
        )
        ODSIndicador.objects.get_or_create(ods=ods_12, indicador=sustentaveis)
        for item in itens:
            VinculoInventarioIndicador.objects.get_or_create(
                indicador=sustentaveis, item=item,
            )
        MedicaoIndicador.objects.get_or_create(
            indicador=sustentaveis, periodo=date(2026, 11, 1),
            defaults={"valor_calculado": sustentaveis.calcular()},
        )

        atendimentos, _ = IndicadorODS.objects.get_or_create(
            nome="[Demo] Atendimentos em ações de turismo",
            defaults={
                "descricao": "Série fictícia de pesquisas para demonstrar o histórico.",
                "meta": "200 atendimentos (exemplo)",
                "regra_calculo": RegraCalculo.MANUAL,
                "regra_descricao": "Soma dos valores registrados nas pesquisas de demonstração.",
            },
        )
        ODSIndicador.objects.get_or_create(ods=ods_8, indicador=atendimentos)
        acumulado = 0
        for periodo, valor in [
            (date(2026, 8, 1), 45),
            (date(2026, 9, 1), 60),
            (date(2026, 10, 1), 75),
        ]:
            DadoPesquisaODS.objects.get_or_create(
                indicador=atendimentos, data_referencia=periodo,
                origem_pesquisa="Pesquisa fictícia para apresentação",
                defaults={"valor": valor, "observacao": "Dado de demonstração."},
            )
            acumulado += valor
            MedicaoIndicador.objects.get_or_create(
                indicador=atendimentos, periodo=periodo,
                defaults={"valor_calculado": acumulado},
            )

        self.stdout.write(self.style.SUCCESS(
            f"Apresentação pronta: {novos} itens fictícios novos; "
            f"{len(exemplos)} itens de demonstração disponíveis."
        ))
