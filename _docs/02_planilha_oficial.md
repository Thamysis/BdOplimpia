# Estrutura da planilha oficial — INVENTARIO OFICIAL OLIMPIA

Fonte: Google Sheets `1pNOrSfs5dLCQUbSu9XIGDYJftfjXLFpFSve_9fWWM0k` (lido via Google Sheets API).

## Organização (37 abas)
- **CONTROLE INVENTÁRIO** (gid 683573059) — aba-resumo: lista as categorias e total inventariado.
- **CADASTUR**, **DADOS CONSOLIDADOS**, **CONTROLE ODS** — abas estruturais/auxiliares.
- ~31 abas de categoria (um segmento cada): MEIOS DE HOSPEDAGEM (231 colunas),
  MEIOS DE ALIMENTAÇÃO E BEBIDAS (177), ESPAÇOS PARA EVENTOS (233),
  ATRATIVOS/LAZER/ENTRETENIMENTO (214), AGÊNCIAS E OPERADORAS (93),
  LOCADORA DE VEÍC. E TRANSP. (59), GUIAS DE TURISMO (37), ARTESANATO (48),
  RHC (44), FARMÁCIAS (35), e várias simples (BANCOS, RELIGIÃO, SUPERMERCADOS,
  etc.) com ~26 colunas.
- Abas PESQUISA_FORNECEDORES (MH/MAB/DEMAIS) e MH IRREGULAR.

## Layout de cada aba de categoria
Linhas 1–2: banner (título da categoria, "ÚLTIMA ATUALIZAÇÃO").
Linhas 3–4: cabeçalhos de GRUPO mesclados ("USO EXCLUSIVO SECRETARIA", "DADOS MH",
"INFORMAÇÕES RESERVAS", "GERAL", "SERVIÇOS E EQUIPAMENTOS").
**Linha de cabeçalho real**: varia por aba (ex.: Hospedagem = linha 5, Bancos = linha 4,
Agências = linha 5). Primeira coluna costuma ser FILTRO/QTD.

## Vocabulário de colunas (comum entre abas) → modelo
| Coluna na planilha | Alvo no modelo |
|---|---|
| NOME FANTASIA / EMPRESA | ItemInventario.nome |
| RAZÃO SOCIAL | ItemInventario.razao_social |
| TIPO | ItemInventario.tipo_documento (ou campo) |
| CNPJ | ItemInventario.documento (tipo_documento="CNPJ") |
| ENDEREÇO | ItemInventario.endereco |
| BAIRRO | ItemInventario.bairro |
| COORDENADAS GEOGRÁFICAS | latitude/longitude (parse "lat, long") |
| TELEFONE / FONE / EMAIL / SITE / FACEBOOK / INSTAGRAM | Contato (tipo/valor) |
| CNAE | Cnae + PossuiAtividade |
| N° CADASTUR / VENCIMENTO CADASTUR / TIPO CADASTUR | Cadastur |
| CLASSIFICAÇÃO, REGIÃO, LOCALIZAÇÃO, UH'S, LEITOS, FUNC. FIXOS/TEMP, EIXO/ODS… | CampoSegmento + Preenchimento (campos específicos por segmento) |

## Conclusão de modelagem
A estrutura real confirma o Modelo Lógico: campos comuns no ItemInventario,
campos específicos por categoria em CampoSegmento/Preenchimento, contatos múltiplos
em Contato, CADASTUR e CNAE em tabelas próprias, e colunas EIXO/ODS alimentando o
Módulo ODS. O importador oficial deve: detectar a linha de cabeçalho, casar nomes de
coluna por sinônimos, extrair base + contatos + cadastur, e jogar o restante como
campos de segmento.
