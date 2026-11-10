"""Pipeline de importação e validação do Inventário (BDP01 / BDP11).

Lê um arquivo tabular (CSV/XLSX/ODS), valida cada linha e classifica em
aceitas e rejeitadas, registrando o motivo de cada rejeição. Suporta dois usos:

* validar(...)  -> apenas confere a integridade e devolve um resumo (BDP11),
  sem gravar itens na base.
* importar(...) -> valida e grava os itens aceitos uma única vez (BDP01).

Campos obrigatórios mínimos da linha: ``nome``. Linhas são consideradas
duplicadas entre si (mesmo nome, sem distinção de caixa/espaços) e também em
relação a itens já existentes no Inventário.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from typing import Iterable

from django.db import transaction

from inventario.models import ItemInventario, StatusItem

from .models import (
    Importacao,
    InconsistenciaImportacao,
    StatusImportacao,
    TipoInconsistencia,
)

CAMPOS_OBRIGATORIOS = ["nome"]
CAMPOS_ITEM = [
    "nome",
    "razao_social",
    "tipo_documento",
    "documento",
    "endereco",
    "bairro",
    "latitude",
    "longitude",
]


@dataclass
class LinhaResultado:
    referencia: str
    dados: dict
    aceita: bool = True
    tipo: str = ""
    motivo: str = ""

    @property
    def tipo_display(self) -> str:
        rotulos = {
            TipoInconsistencia.DUPLICIDADE: "Duplicidade",
            TipoInconsistencia.CAMPO_OBRIGATORIO: "Campo obrigatório ausente",
            TipoInconsistencia.FORMATO: "Formato inválido",
        }
        return rotulos.get(self.tipo, self.tipo)


@dataclass
class ResultadoValidacao:
    total_lidos: int = 0
    aceitas: list = field(default_factory=list)
    rejeitadas: list = field(default_factory=list)

    @property
    def total_aceitas(self) -> int:
        return len(self.aceitas)

    @property
    def total_rejeitadas(self) -> int:
        return len(self.rejeitadas)


class ArquivoNaoSuportado(Exception):
    pass


# --- Leitura de arquivos -------------------------------------------------

def _normaliza_cabecalho(nome: str) -> str:
    return (nome or "").strip().lower().replace(" ", "_")


def ler_linhas(conteudo: bytes, nome_arquivo: str) -> list[dict]:
    """Devolve uma lista de dicionários {coluna: valor} a partir do arquivo."""
    nome = (nome_arquivo or "").lower()
    if nome.endswith(".csv") or nome.endswith(".txt") or not nome:
        return _ler_csv(conteudo)
    if nome.endswith(".xlsx"):
        return _ler_xlsx(conteudo)
    if nome.endswith(".ods"):
        return _ler_ods(conteudo)
    # Tenta CSV como fallback.
    return _ler_csv(conteudo)


def _ler_csv(conteudo: bytes) -> list[dict]:
    texto = conteudo.decode("utf-8-sig")
    # Detecta separador (vírgula ou ponto e vírgula).
    amostra = texto.splitlines()[0] if texto.splitlines() else ""
    delimitador = ";" if amostra.count(";") > amostra.count(",") else ","
    leitor = csv.DictReader(io.StringIO(texto), delimiter=delimitador)
    linhas = []
    for linha in leitor:
        linhas.append({_normaliza_cabecalho(k): (v or "").strip() for k, v in linha.items()})
    return linhas


def _ler_xlsx(conteudo: bytes) -> list[dict]:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:  # pragma: no cover - depende do ambiente
        raise ArquivoNaoSuportado(
            "Leitura de XLSX requer o pacote openpyxl. Use CSV ou instale openpyxl."
        ) from exc
    wb = load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
    ws = wb.active
    linhas_iter = ws.iter_rows(values_only=True)
    try:
        cabecalho = [_normaliza_cabecalho(str(c)) for c in next(linhas_iter)]
    except StopIteration:
        return []
    linhas = []
    for valores in linhas_iter:
        registro = {}
        for col, valor in zip(cabecalho, valores):
            registro[col] = "" if valor is None else str(valor).strip()
        linhas.append(registro)
    return linhas


def _ler_ods(conteudo: bytes) -> list[dict]:  # pragma: no cover - opcional
    try:
        from odf.opendocument import load
        from odf.table import Table, TableRow, TableCell
        from odf.text import P
    except ImportError as exc:
        raise ArquivoNaoSuportado(
            "Leitura de ODS requer o pacote odfpy. Use CSV ou instale odfpy."
        ) from exc
    doc = load(io.BytesIO(conteudo))
    tabela = doc.spreadsheet.getElementsByType(Table)[0]
    linhas_raw = []
    for row in tabela.getElementsByType(TableRow):
        celulas = []
        for cell in row.getElementsByType(TableCell):
            textos = cell.getElementsByType(P)
            celulas.append("".join(str(t) for t in textos).strip())
        linhas_raw.append(celulas)
    if not linhas_raw:
        return []
    cabecalho = [_normaliza_cabecalho(c) for c in linhas_raw[0]]
    linhas = []
    for valores in linhas_raw[1:]:
        linhas.append({c: v for c, v in zip(cabecalho, valores)})
    return linhas


# --- Validação -----------------------------------------------------------

def _chave_duplicidade(dados: dict) -> str:
    return " ".join((dados.get("nome") or "").lower().split())


def validar_linhas(linhas: Iterable[dict]) -> ResultadoValidacao:
    """Classifica as linhas em aceitas e rejeitadas (sem gravar)."""
    resultado = ResultadoValidacao()
    nomes_existentes = {
        " ".join(n.lower().split())
        for n in ItemInventario.objects.values_list("nome", flat=True)
    }
    vistos: set[str] = set()

    for indice, dados in enumerate(linhas, start=1):
        resultado.total_lidos += 1
        referencia = f"linha {indice}"

        # 1) Campos obrigatórios.
        faltando = [c for c in CAMPOS_OBRIGATORIOS if not (dados.get(c) or "").strip()]
        if faltando:
            resultado.rejeitadas.append(
                LinhaResultado(
                    referencia=referencia,
                    dados=dados,
                    aceita=False,
                    tipo=TipoInconsistencia.CAMPO_OBRIGATORIO,
                    motivo=f"Campo obrigatório ausente: {', '.join(faltando)}.",
                )
            )
            continue

        chave = _chave_duplicidade(dados)
        # 2) Duplicidade dentro do próprio arquivo ou com a base existente.
        if chave in vistos or chave in nomes_existentes:
            resultado.rejeitadas.append(
                LinhaResultado(
                    referencia=referencia,
                    dados=dados,
                    aceita=False,
                    tipo=TipoInconsistencia.DUPLICIDADE,
                    motivo=f"Registro duplicado para o nome '{dados.get('nome')}'.",
                )
            )
            continue

        # 3) Formato de coordenadas, quando informadas.
        erro_formato = _valida_coordenadas(dados)
        if erro_formato:
            resultado.rejeitadas.append(
                LinhaResultado(
                    referencia=referencia,
                    dados=dados,
                    aceita=False,
                    tipo=TipoInconsistencia.FORMATO,
                    motivo=erro_formato,
                )
            )
            continue

        vistos.add(chave)
        resultado.aceitas.append(
            LinhaResultado(referencia=referencia, dados=dados, aceita=True)
        )
    return resultado


def _valida_coordenadas(dados: dict) -> str:
    for campo, minimo, maximo in (("latitude", -90, 90), ("longitude", -180, 180)):
        bruto = (dados.get(campo) or "").strip().replace(",", ".")
        if not bruto:
            continue
        try:
            valor = float(bruto)
        except ValueError:
            return f"{campo.capitalize()} inválida: '{dados.get(campo)}'."
        if not (minimo <= valor <= maximo):
            return f"{campo.capitalize()} fora da faixa [{minimo}, {maximo}]."
    return ""


def _dados_item(dados: dict) -> dict:
    limpos = {}
    for campo in CAMPOS_ITEM:
        valor = (dados.get(campo) or "").strip()
        if campo in ("latitude", "longitude"):
            valor = valor.replace(",", ".")
            limpos[campo] = valor or None
        else:
            limpos[campo] = valor
    return limpos


# --- Prévia (não grava nada) ---------------------------------------------

def gerar_previa(conteudo, nome_arquivo) -> ResultadoValidacao:
    """Lê e classifica as linhas para exibição da prévia, sem tocar na base."""
    linhas = ler_linhas(conteudo, nome_arquivo)
    return validar_linhas(linhas)


# --- Persistência --------------------------------------------------------

def _registra_inconsistencias(importacao: Importacao, resultado: ResultadoValidacao):
    registros = [
        InconsistenciaImportacao(
            importacao=importacao,
            referencia_origem=linha.referencia,
            tipo=linha.tipo,
            descricao=linha.motivo,
        )
        for linha in resultado.rejeitadas
    ]
    if registros:
        InconsistenciaImportacao.objects.bulk_create(registros)


@transaction.atomic
def validar(conteudo, nome_arquivo, usuario=None, fonte=None) -> Importacao:
    """BDP11 — valida integridade e registra inconsistências, sem gravar itens."""
    linhas = ler_linhas(conteudo, nome_arquivo)
    resultado = validar_linhas(linhas)
    importacao = Importacao.objects.create(
        usuario=usuario,
        fonte=fonte,
        arquivo_origem=nome_arquivo,
        status=(
            StatusImportacao.COM_INCONSISTENCIAS
            if resultado.total_rejeitadas
            else StatusImportacao.VALIDADA
        ),
        qtd_registros=resultado.total_lidos,
        qtd_importados=0,
        qtd_rejeitados=resultado.total_rejeitadas,
    )
    _registra_inconsistencias(importacao, resultado)
    importacao.resultado = resultado  # anexado em memória para a view
    return importacao


@transaction.atomic
def importar(conteudo, nome_arquivo, usuario=None, fonte=None) -> Importacao:
    """BDP01 — valida e grava os itens aceitos uma única vez."""
    from auditoria.services import registrar_criacao

    linhas = ler_linhas(conteudo, nome_arquivo)
    resultado = validar_linhas(linhas)

    for linha in resultado.aceitas:
        item = ItemInventario.objects.create(
            status=StatusItem.ATIVO, **_dados_item(linha.dados)
        )
        registrar_criacao(item, usuario=usuario)

    importacao = Importacao.objects.create(
        usuario=usuario,
        fonte=fonte,
        arquivo_origem=nome_arquivo,
        status=(
            StatusImportacao.COM_INCONSISTENCIAS
            if resultado.total_rejeitadas
            else StatusImportacao.CONCLUIDA
        ),
        qtd_registros=resultado.total_lidos,
        qtd_importados=resultado.total_aceitas,
        qtd_rejeitados=resultado.total_rejeitadas,
    )
    _registra_inconsistencias(importacao, resultado)
    importacao.resultado = resultado
    return importacao
