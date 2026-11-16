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
    erro: str = ""


@dataclass
class PreviaOficial:
    aceitas: list[tuple[str, LinhaOficial]] = field(default_factory=list)
    rejeitadas: list[dict] = field(default_factory=list)
    abas: list[str] = field(default_factory=list)

    @property
    def total_lidos(self):
        return len(self.aceitas) + len(self.rejeitadas)


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


def interpretar(linhas: list[list], nome_segmento: str = "", rejeitadas=None) -> list[LinhaOficial]:
    """Converte a matriz bruta de uma aba de categoria em LinhaOficial por item."""
    idx_cab = detectar_linha_cabecalho(linhas)
    if idx_cab < 0:
        return []

    cabecalhos = [_norm(c) for c in linhas[idx_cab]]
    mapeamento = [_casar_coluna(c) for c in cabecalhos]
    indice_ordem = next(
        (i for i, c in enumerate(cabecalhos) if c in {"qtd", "qtde", "q t d."}), None
    )

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
                    if lat is None or lon is None:
                        registro.erro = f"Coordenadas inválidas: {valor}."
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

        ordem = valores[indice_ordem] if indice_ordem is not None and indice_ordem < len(valores) else ""
        tem_ordem = ordem.isdigit() and int(ordem) > 0
        tem_dados = any(
            v for k, v in registro.base.items()
            if k != "nome" and v is not None
        ) or bool(registro.contatos or registro.cadastur or registro.cnae)
        # Blocos de totais e classificação da própria planilha não são estabelecimentos.
        if nome_candidato and not _eh_rotulo_total(nome_candidato) and (tem_ordem or tem_dados):
            if registro.base.get("documento") and not registro.base.get("tipo_documento"):
                doc = registro.base["documento"]
                registro.base["tipo_documento"] = "CNPJ" if len(re.sub(r"\D", "", doc)) > 11 else "CPF"
            resultados.append(registro)
        elif not nome_candidato and rejeitadas is not None and (tem_ordem or tem_dados) and not any(
            _eh_rotulo_total(v) for v in valores if v
        ):
            rejeitadas.append({
                "referencia": f"{nome_segmento}: linha {n}",
                "tipo": "campo_obrigatorio", "motivo": "Nome ausente.",
            })
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

    from auditoria.services import (
        registrar_criacao, registrar_edicao, registrar_relacao, snapshot, snapshot_relacoes,
    )
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
            anterior = snapshot(item) if not criado else None
            relacoes_antes = snapshot_relacoes(item) if not criado else None
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

            if not criado:
                edicoes = registrar_edicao(item, anterior, usuario=usuario)
                relacoes_depois = snapshot_relacoes(item)
                mudou_relacao = False
                for campo, valor_anterior in relacoes_antes.items():
                    if valor_anterior != relacoes_depois[campo]:
                        registrar_relacao(
                            item, campo, valor_anterior, relacoes_depois[campo], usuario=usuario
                        )
                        mudou_relacao = True
                if edicoes or mudou_relacao:
                    resumo["atualizados"] += 1

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
        from .services import ler_tabelas_ods

        return next((linhas for _, linhas in ler_tabelas_ods(conteudo)), [])
    # CSV / texto
    texto = conteudo.decode("utf-8-sig")
    amostra = texto.splitlines()[0] if texto.splitlines() else ""
    delimitador = ";" if amostra.count(";") > amostra.count(",") else ","
    return [list(r) for r in csv.reader(io.StringIO(texto), delimiter=delimitador)]


def ler_abas(conteudo: bytes, nome_arquivo: str, segmento: str = ""):
    """Devolve matrizes de todas as abas de categoria de um XLSX oficial."""
    nome = nome_arquivo.lower()
    if nome.endswith(".xlsx"):
        import io
        from openpyxl import load_workbook

        wb = load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
        try:
            folhas = wb.worksheets
            if segmento:
                candidatas = [s for s in folhas if _norm(s.title) == _norm(segmento)]
                folhas = candidatas or ([wb.active] if len(folhas) == 1 else [])
                if not folhas:
                    raise ValueError(f"A aba '{segmento}' não foi encontrada no arquivo.")
            for folha in folhas:
                matriz = [list(row) for row in folha.iter_rows(values_only=True)]
                if detectar_linha_cabecalho(matriz) >= 0:
                    yield (segmento or folha.title.strip(), matriz)
        finally:
            wb.close()
        return
    if nome.endswith(".ods"):
        from .services import ler_tabelas_ods

        for nome_aba, matriz in ler_tabelas_ods(conteudo):
            if segmento and _norm(nome_aba) != _norm(segmento):
                continue
            if detectar_linha_cabecalho(matriz) >= 0:
                yield (segmento or nome_aba.strip(), matriz)
        return
    if not segmento:
        raise ValueError("Informe o segmento ao enviar um arquivo CSV.")
    matriz = ler_matriz(conteudo, nome_arquivo)
    if detectar_linha_cabecalho(matriz) >= 0:
        yield segmento, matriz


def preparar(conteudo: bytes, nome_arquivo: str, segmento: str = "") -> PreviaOficial:
    """Classifica o Inventário oficial antes de gravar qualquer item."""
    previa = PreviaOficial()
    vistos = set()
    for nome_aba, matriz in ler_abas(conteudo, nome_arquivo, segmento):
        previa.abas.append(nome_aba)
        registros = interpretar(matriz, nome_aba, previa.rejeitadas)
        for registro in registros:
            referencia = f"{nome_aba}: {registro.referencia}"
            chave = (_norm(nome_aba), _norm(registro.base.get("nome")))
            if registro.erro:
                previa.rejeitadas.append({
                    "referencia": referencia, "tipo": "formato", "motivo": registro.erro,
                })
            elif chave in vistos:
                previa.rejeitadas.append({
                    "referencia": referencia, "tipo": "duplicidade",
                    "motivo": "Nome repetido na mesma aba.",
                })
            else:
                vistos.add(chave)
                previa.aceitas.append((nome_aba, registro))
    if not previa.abas:
        raise ValueError("Nenhuma aba com cabeçalho de Inventário foi encontrada.")
    return previa


def confirmar_previa(preview: PreviaOficial, nome_arquivo: str, usuario=None):
    """Grava registros aceitos e registra a carga e as inconsistências."""
    from collections import defaultdict

    from django.db import transaction

    from .models import Importacao, InconsistenciaImportacao, StatusImportacao

    por_segmento = defaultdict(list)
    for segmento, registro in preview.aceitas:
        por_segmento[segmento].append(registro)
    resumo = {"criados": 0, "atualizados": 0, "ignorados": 0}
    with transaction.atomic():
        for segmento, registros in por_segmento.items():
            parcial = persistir(registros, segmento, usuario=usuario)
            for chave in resumo:
                resumo[chave] += parcial[chave]
        carga = Importacao.objects.create(
            usuario=usuario, arquivo_origem=nome_arquivo,
            status=(StatusImportacao.COM_INCONSISTENCIAS if preview.rejeitadas
                    else StatusImportacao.CONCLUIDA),
            qtd_registros=preview.total_lidos,
            qtd_importados=len(preview.aceitas),
            qtd_rejeitados=len(preview.rejeitadas),
        )
        InconsistenciaImportacao.objects.bulk_create([
            InconsistenciaImportacao(
                importacao=carga, referencia_origem=erro["referencia"][:120],
                tipo=erro["tipo"], descricao=erro["motivo"][:255],
            ) for erro in preview.rejeitadas
        ])
    return carga, resumo


def importar_arquivo(conteudo: bytes, nome_arquivo: str, nome_segmento: str, usuario=None):
    """Lê o arquivo, interpreta no formato oficial e persiste. Retorna (registros, resumo)."""
    matriz = ler_matriz(conteudo, nome_arquivo)
    registros = interpretar(matriz, nome_segmento)
    resumo = persistir(registros, nome_segmento, usuario=usuario)
    return registros, resumo
