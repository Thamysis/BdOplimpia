"""Importador do formato oficial da planilha INVENTARIO OFICIAL OLIMPIA.

As abas de categoria da planilha oficial têm um layout específico:
* linhas iniciais com banner e cabeçalhos de grupo mesclados;
* uma linha de cabeçalho real cuja posição varia por aba;
* colunas com vocabulário recorrente (NOME FANTASIA, RAZÃO SOCIAL, CNPJ,
  ENDEREÇO, BAIRRO, COORDENADAS GEOGRÁFICAS, TELEFONE, EMAIL, CNAE, CADASTUR…)
  além de muitas colunas específicas da categoria.

Este módulo normaliza esse formato: detecta a linha de cabeçalho, casa as colunas
conhecidas por sinônimos e separa cada linha em:
* campos-base do ItemInventario;
* contatos (telefone, e-mail, site, redes);
* dados de Cadastur;
* campos específicos do segmento (o restante das colunas preenchidas).

Trabalha sobre uma matriz de linhas (lista de listas de strings), que pode vir de
um XLSX/ODS/CSV já lido ou diretamente da API do Google Sheets.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field


def _norm(texto) -> str:
    """Remove acentos, quebras de linha e espaços extras; caixa baixa."""
    if texto is None:
        return ""
    s = str(texto)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("\n", " ").replace("\r", " ")
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


# Sinônimos de colunas-base -> nome canônico do campo do ItemInventario.
MAPA_BASE = {
    "nome": ["nome fantasia", "empresa", "nome", "razao social / nome fantasia"],
    "razao_social": ["razao social"],
    "documento": ["cnpj", "cpf", "cnpj/cpf", "documento"],
    "endereco": ["endereco"],
    "bairro": ["bairro"],
    "coordenadas": ["coordenadas geograficas", "coordenadas"],
}

MAPA_CONTATO = {
    "telefone": ["telefone comercial", "fone", "telefone", "tel"],
    "email": ["email comercial", "email", "e-mail"],
    "site": ["site"],
    "facebook": ["facebook"],
    "instagram": ["instagram"],
}

MAPA_CADASTUR = {
    "numero": ["numero cadastro cadastur", "n° do cadastur", "n do cadastur", "numero cadastur"],
    "vencimento": ["vencimento cadastur"],
    "tipo": ["tipo cadastur"],
}

CNAE_SINONIMOS = ["cnae"]

# Colunas estruturais/ruído que não viram campo de segmento.
IGNORAR = {
    "", "qtd", "qtde", "q t d.", "total", "filtro d= destinos inteligentes",
    "dados pddt", "dados plano diretor", "dados mh", "inventario",
    "uso exclusivo secretaria", "geral",
}


@dataclass
class LinhaOficial:
    referencia: str
    base: dict = field(default_factory=dict)
    contatos: list = field(default_factory=list)   # [(tipo, valor)]
    cadastur: dict = field(default_factory=dict)
    cnae: str = ""
    campos_segmento: dict = field(default_factory=dict)  # {nome_campo: valor}


def _casar_coluna(cabecalho_norm: str):
    """Devolve ('base'|'contato'|'cadastur'|'cnae'|'segmento', chave)."""
    for canonico, sinonimos in MAPA_BASE.items():
        if cabecalho_norm in sinonimos:
            return "base", canonico
    for canonico, sinonimos in MAPA_CONTATO.items():
        if cabecalho_norm in sinonimos:
            return "contato", canonico
    for canonico, sinonimos in MAPA_CADASTUR.items():
        if cabecalho_norm in sinonimos:
            return "cadastur", canonico
    if cabecalho_norm in CNAE_SINONIMOS:
        return "cnae", "cnae"
    return "segmento", cabecalho_norm


def detectar_linha_cabecalho(linhas: list[list]) -> int:
    """Encontra o índice (0-based) da linha de cabeçalho real.

    É a linha que contém o maior número de colunas-base conhecidas
    (nome/empresa, endereco, etc.). Procura nas 15 primeiras linhas.
    """
    alvos = set()
    for sinonimos in MAPA_BASE.values():
        alvos.update(sinonimos)
    alvos.update({"empresa", "nome fantasia", "endereco", "coordenadas geograficas"})

    melhor_idx, melhor_pontuacao = -1, 0
    for i, linha in enumerate(linhas[:15]):
        pontuacao = sum(1 for celula in linha if _norm(celula) in alvos)
        if pontuacao > melhor_pontuacao:
            melhor_idx, melhor_pontuacao = i, pontuacao
    return melhor_idx if melhor_pontuacao >= 2 else -1


def _parse_coordenadas(valor: str):
    """Extrai (lat, long) de um texto como '-21,73, -48,91' ou '-21.73 -48.91'."""
    if not valor:
        return None, None
    nums = re.findall(r"-?\d{1,3}(?:[.,]\d+)?", str(valor))
    if len(nums) >= 2:
        def conv(n):
            n = n.replace(",", ".")
            try:
                return float(n)
            except ValueError:
                return None
        lat, lon = conv(nums[0]), conv(nums[1])
        if lat is not None and -90 <= lat <= 90 and lon is not None and -180 <= lon <= 180:
            return lat, lon
    return None, None


def interpretar(linhas: list[list], nome_segmento: str = "") -> list[LinhaOficial]:
    """Converte a matriz bruta de uma aba de categoria em LinhaOficial por item."""
    idx_cab = detectar_linha_cabecalho(linhas)
    if idx_cab < 0:
        return []

    cabecalhos = [_norm(c) for c in linhas[idx_cab]]
    mapeamento = [_casar_coluna(c) for c in cabecalhos]

    resultados: list[LinhaOficial] = []
    for n, linha in enumerate(linhas[idx_cab + 1 :], start=idx_cab + 2):
        # Ignora linhas vazias ou de total.
        valores = [("" if c is None else str(c).strip()) for c in linha]
        if not any(valores):
            continue
        nome_candidato = ""
        registro = LinhaOficial(referencia=f"linha {n}")

        for col_i, (tipo, chave) in enumerate(mapeamento):
            valor = valores[col_i] if col_i < len(valores) else ""
            if not valor:
                continue
            cab_original = cabecalhos[col_i] if col_i < len(cabecalhos) else ""
            if cab_original in IGNORAR:
                continue

            if tipo == "base":
                if chave == "coordenadas":
                    lat, lon = _parse_coordenadas(valor)
                    registro.base["latitude"] = lat
                    registro.base["longitude"] = lon
                else:
                    registro.base[chave] = valor
                    if chave == "nome":
                        nome_candidato = valor
            elif tipo == "contato":
                registro.contatos.append((chave, valor))
            elif tipo == "cadastur":
                registro.cadastur[chave] = valor
            elif tipo == "cnae":
                registro.cnae = valor
            else:  # segmento
                if cab_original and cab_original not in IGNORAR:
                    registro.campos_segmento[cab_original] = valor

        # Linha só é item se tiver um nome válido (não um rótulo de total).
        if nome_candidato and not _eh_rotulo_total(nome_candidato):
            if registro.base.get("documento") and not registro.base.get("tipo_documento"):
                doc = registro.base["documento"]
                registro.base["tipo_documento"] = "CNPJ" if len(re.sub(r"\D", "", doc)) > 11 else "CPF"
            resultados.append(registro)
    return resultados


def _eh_rotulo_total(valor: str) -> bool:
    """Reconhece linhas agregadas da planilha (TOTAL, TOTAIS DE…, SUBTOTAL)."""
    v = _norm(valor)
    return v in {"total", "totais", "subtotal"} or v.startswith("total ") or v.startswith("totais ")


# --- Persistência no modelo relacional -----------------------------------

def _tipo_dado_do_valor(valor: str):
    from inventario.models import CampoSegmento

    v = (valor or "").strip().replace(",", ".")
    try:
        float(v)
        return CampoSegmento.TipoDado.NUMERO
    except ValueError:
        return CampoSegmento.TipoDado.TEXTO


def persistir(registros: list["LinhaOficial"], nome_segmento: str, usuario=None) -> dict:
    """Grava os registros interpretados no modelo. Idempotente por (nome, segmento).

    Devolve um resumo {criados, atualizados, ignorados}.
    """
    from django.db import transaction

    from auditoria.services import registrar_criacao
    from inventario.models import (
        Cadastur,
        CampoSegmento,
        Cnae,
        Contato,
        ItemInventario,
        Participa,
        Preenchimento,
        PossuiAtividade,
        Segmento,
        StatusItem,
    )

    resumo = {"criados": 0, "atualizados": 0, "ignorados": 0}

    with transaction.atomic():
        segmento, _ = Segmento.objects.get_or_create(nome=nome_segmento)
        # Cache de campos do segmento.
        campos_cache = {c.nome: c for c in segmento.campos.all()}

        for reg in registros:
            nome = reg.base.get("nome", "").strip()
            if not nome:
                resumo["ignorados"] += 1
                continue

            dados_item = {
                k: v
                for k, v in reg.base.items()
                if k in ("nome", "razao_social", "tipo_documento", "documento",
                         "endereco", "bairro", "latitude", "longitude")
            }
            item, criado = ItemInventario.objects.get_or_create(
                nome=nome, defaults={**dados_item, "status": StatusItem.ATIVO}
            )
            if criado:
                registrar_criacao(item, usuario=usuario)
                resumo["criados"] += 1
            else:
                # Atualiza apenas campos vazios para não sobrescrever curadoria manual.
                alterou = False
                for k, v in dados_item.items():
                    if v and not getattr(item, k):
                        setattr(item, k, v)
                        alterou = True
                if alterou:
                    item.save()
                    resumo["atualizados"] += 1

            Participa.objects.get_or_create(item=item, segmento=segmento)

            # Campos específicos do segmento.
            for nome_campo, valor in reg.campos_segmento.items():
                campo = campos_cache.get(nome_campo)
                if campo is None:
                    campo = CampoSegmento.objects.create(
                        segmento=segmento,
                        nome=nome_campo,
                        tipo_dado=_tipo_dado_do_valor(valor),
                    )
                    campos_cache[nome_campo] = campo
                Preenchimento.objects.update_or_create(
                    item=item, campo=campo, defaults={"valor": valor}
                )

            # Contatos.
            for tipo, valor in reg.contatos:
                Contato.objects.get_or_create(
                    item=item, tipo=tipo, valor=valor, defaults={"finalidade": ""}
                )

            # Cadastur.
            if reg.cadastur.get("numero"):
                Cadastur.objects.get_or_create(
                    item=item,
                    numero=reg.cadastur["numero"],
                    defaults={
                        "tipo": reg.cadastur.get("tipo", ""),
                        "situacao": "",
                    },
                )

            # CNAE.
            if reg.cnae:
                codigo = reg.cnae.strip()[:15]
                cnae, _ = Cnae.objects.get_or_create(
                    codigo=codigo, defaults={"descricao": ""}
                )
                PossuiAtividade.objects.get_or_create(item=item, cnae=cnae)

    return resumo


# --- Leitura de arquivo em matriz (para o formato oficial) ---------------

def ler_matriz(conteudo: bytes, nome_arquivo: str) -> list[list]:
    """Lê CSV/XLSX/ODS como matriz de linhas (lista de listas de strings)."""
    import csv
    import io

    nome = (nome_arquivo or "").lower()
    if nome.endswith(".xlsx"):
        from openpyxl import load_workbook

        wb = load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
        ws = wb.active
        return [
            ["" if c is None else str(c) for c in row]
            for row in ws.iter_rows(values_only=True)
        ]
    if nome.endswith(".ods"):
        from .services import _ler_ods  # type: ignore

        # Reaproveita o leitor ODS, reconstruindo a matriz a partir dos dicts.
        registros = _ler_ods(conteudo)
        if not registros:
            return []
        cabecalhos = list(registros[0].keys())
        matriz = [cabecalhos]
        for r in registros:
            matriz.append([r.get(c, "") for c in cabecalhos])
        return matriz
    # CSV / texto
    texto = conteudo.decode("utf-8-sig")
    amostra = texto.splitlines()[0] if texto.splitlines() else ""
    delimitador = ";" if amostra.count(";") > amostra.count(",") else ","
    return [list(r) for r in csv.reader(io.StringIO(texto), delimiter=delimitador)]


def importar_arquivo(conteudo: bytes, nome_arquivo: str, nome_segmento: str, usuario=None):
    """Lê o arquivo, interpreta no formato oficial e persiste. Retorna (registros, resumo)."""
    matriz = ler_matriz(conteudo, nome_arquivo)
    registros = interpretar(matriz, nome_segmento)
    resumo = persistir(registros, nome_segmento, usuario=usuario)
    return registros, resumo
