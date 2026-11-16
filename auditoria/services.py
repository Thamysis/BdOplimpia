"""Serviços de auditoria: comparam estados de um item e geram o histórico."""
from inventario.models import ItemInventario

from .models import AcaoAuditoria, AlteracaoInventario

#: Campos de negócio monitorados do item.
CAMPOS_MONITORADOS = [
    "nome",
    "razao_social",
    "tipo_documento",
    "documento",
    "endereco",
    "bairro",
    "latitude",
    "longitude",
    "status",
]


def _valor(item, campo):
    v = getattr(item, campo)
    return "" if v is None else str(v)


def registrar_criacao(item: ItemInventario, usuario=None):
    AlteracaoInventario.objects.create(
        usuario=usuario,
        item=item,
        acao=AcaoAuditoria.CRIACAO,
        campo_alterado="",
        valor_anterior="",
        valor_novo=item.nome,
    )


def registrar_edicao(item: ItemInventario, anterior: dict, usuario=None):
    """Registra uma linha de histórico por campo alterado (BDP03).

    ``anterior`` é um dicionário {campo: valor_antigo} capturado antes de salvar.
    """
    registros = []
    for campo in CAMPOS_MONITORADOS:
        valor_antigo = "" if anterior.get(campo) is None else str(anterior.get(campo))
        valor_atual = _valor(item, campo)
        if valor_antigo != valor_atual:
            acao = AcaoAuditoria.EDICAO
            if campo == "status":
                acao = (
                    AcaoAuditoria.INATIVACAO
                    if valor_atual == "inativo"
                    else AcaoAuditoria.REATIVACAO
                )
            registros.append(
                AlteracaoInventario(
                    usuario=usuario,
                    item=item,
                    acao=acao,
                    campo_alterado=campo,
                    valor_anterior=valor_antigo,
                    valor_novo=valor_atual,
                )
            )
    if registros:
        AlteracaoInventario.objects.bulk_create(registros)
    return registros


def snapshot(item: ItemInventario) -> dict:
    """Captura o estado atual dos campos monitorados."""
    return {campo: getattr(item, campo) for campo in CAMPOS_MONITORADOS}


def registrar_relacao(item: ItemInventario, campo: str, anterior, atual, usuario=None):
    """Registra alterações de vínculos e dados complementares do Inventário."""
    if anterior == atual:
        return None
    return AlteracaoInventario.objects.create(
        usuario=usuario, item=item, acao=AcaoAuditoria.EDICAO,
        campo_alterado=campo, valor_anterior=str(anterior), valor_novo=str(atual),
    )


def snapshot_relacoes(item: ItemInventario) -> dict[str, str]:
    """Resumo estável das relações exibidas no detalhe do item."""
    return {
        "segmentos": "; ".join(sorted(
            item.segmentos.values_list("nome", flat=True)
        )),
        "campos de segmento": "; ".join(sorted(
            f"{p.campo.nome}: {p.valor}" for p in item.preenchimentos.select_related("campo")
        )),
        "contatos": "; ".join(sorted(
            f"{c.tipo}: {c.valor} ({c.finalidade})" for c in item.contato_set.all()
        )),
        "Cadastur": "; ".join(sorted(
            f"{c.numero}: {c.tipo}, {c.situacao}, {c.vencimento or ''}"
            for c in item.cadastur_set.all()
        )),
        "CNAE": "; ".join(sorted(item.atividades.values_list("codigo", flat=True))),
        "profissionais": "; ".join(sorted(item.profissionais.values_list("nome", flat=True))),
    }
