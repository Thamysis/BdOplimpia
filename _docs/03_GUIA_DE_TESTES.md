# OTO — Base de Dados Principal — Guia de Execução e Testes

Guia completo para **rodar o sistema localmente** e **testar todos os casos** — manual
e automatizado. Escrito para humanos e para agentes. Todos os comandos assumem a raiz do
projeto (`/Users/enzopagotto/BdOplimpia`) e o Python do ambiente virtual (`.venv/bin/python`).

> Resumo rápido: `migrate` → `seed_demo` → `runserver` → abrir `http://127.0.0.1:8000/`.
> Testes: `.venv/bin/python manage.py test`. Hoje há **54 testes**, todos verdes.

---

## 1. Pré-requisitos

- Python 3.12+ (o ambiente de referência usa 3.14; a CI usa 3.12).
- Nenhum banco externo é necessário para rodar/testar: o padrão é **SQLite**.
- Dependências em `requirements.txt`: Django 5.2, psycopg (PostgreSQL opcional), openpyxl (XLSX).

### 1.1 Criar/instalar o ambiente (se ainda não existir)

```bash
cd /Users/enzopagotto/BdOplimpia
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

---

## 2. Subir o sistema localmente (passo a passo)

```bash
cd /Users/enzopagotto/BdOplimpia
.venv/bin/python manage.py migrate        # cria db.sqlite3 e todas as tabelas
.venv/bin/python manage.py seed_demo       # dados de demonstração (idempotente)
.venv/bin/python manage.py runserver       # sobe em http://127.0.0.1:8000/
```

Abra **http://127.0.0.1:8000/** → tela de login.

### 2.1 Contas criadas pelo `seed_demo` (senha para todas: `demo12345`)

| Usuário | Perfil | Acesso |
|---|---|---|
| `admin_oto` | Administrador | Tudo: Inventário, Importação, ODS, Usuários, `/admin/` |
| `operador_oto` | Operador | Inventário (cadastrar/editar/consultar/inativar), dados de pesquisa |
| `gestor_oto` | Gestor | ODS (indicadores, medições, histórico) |

O `seed_demo` também cria os **18 segmentos reais** do Inventário Oficial de Olímpia,
4 itens de exemplo e 1 indicador ODS com regra de cálculo.

### 2.2 Criar um superusuário próprio (opcional)

```bash
.venv/bin/python manage.py createsuperuser
```

### 2.3 Começar de um banco limpo (opcional)

```bash
rm -f db.sqlite3
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo
```

### 2.4 Rodar com PostgreSQL (opcional)

Defina as variáveis de ambiente e rode normalmente (o `settings.py` troca para Postgres
quando `POSTGRES_DB` existe):

```bash
export POSTGRES_DB=oto POSTGRES_USER=postgres POSTGRES_PASSWORD=senha \
       POSTGRES_HOST=localhost POSTGRES_PORT=5432
export DJANGO_SECRET_KEY="troque-isto"
.venv/bin/python manage.py migrate
```

---

## 3. Mapa de rotas (para teste manual)

| Rota | Nome | Quem acessa | História |
|---|---|---|---|
| `/` | painel | autenticado | — |
| `/acesso/login/` | login | todos | BDP13 |
| `/acesso/logout/` | logout | autenticado | BDP13 |
| `/acesso/usuarios/` | usuario_lista | administrador | BDP13 |
| `/acesso/usuarios/novo/` | usuario_novo | administrador | BDP13 |
| `/acesso/usuarios/<id>/editar/` | usuario_editar | administrador | BDP13 |
| `/inventario/` | lista | autenticado | BDP04 |
| `/inventario/relatorios/` | relatorios | autenticado | relatórios visuais |
| `/inventario/novo/` | novo | operador/admin | BDP02 |
| `/inventario/<id>/` | detalhe | autenticado | BDP03/05 |
| `/inventario/<id>/editar/` | editar | operador/admin | BDP03 |
| `/inventario/<id>/inativar/` | inativar | operador/admin | BDP05 |
| `/inventario/<id>/reativar/` | reativar | operador/admin | BDP05 |
| `/importacao/` | importar | administrador | BDP01/BDP11 |
| `/importacao/oficial/` | importar_oficial | administrador | BDP01 (planilha oficial) |
| `/importacao/confirmar/` | confirmar | administrador | BDP01 |
| `/importacao/cancelar/` | cancelar | administrador | BDP01 |
| `/importacao/historico/` | historico | administrador | — |
| `/importacao/<id>/` | detalhe | administrador | — |
| `/ods/` | indicador_lista | gestor/admin | BDP08 |
| `/ods/novo/` | indicador_novo | gestor/admin | BDP08 |
| `/ods/<id>/` | indicador_detalhe | gestor/admin | BDP12 |
| `/ods/<id>/calcular/` | calcular_medicao | gestor/admin | BDP10 |
| `/ods/dados-pesquisa/novo/` | dado_pesquisa_novo | gestor/admin | BDP09 |
| `/admin/` | Django admin | staff | — |
| `/health/` | health | público | — |

---

## 4. Roteiro de teste manual — cobertura completa por história

Abra o navegador em `http://127.0.0.1:8000/`. Cada caso lista o **objetivo**, os
**passos** e o **resultado esperado**.

### 4.1 BDP13 — Autenticação e permissões

**Caso 4.1.1 — Login válido**
1. Acesse `/acesso/login/`, entre com `operador_oto` / `demo12345`.
   → Redireciona ao painel `/`.

**Caso 4.1.2 — Login inválido**
1. Tente `operador_oto` / `senhaerrada`.
   → Permanece no login com mensagem de erro; não entra.

**Caso 4.1.3 — Logout encerra sessão**
1. Logado, clique em **Sair**. Depois tente abrir `/inventario/novo/`.
   → Redireciona para o login.

**Caso 4.1.4 — Operador NÃO gerencia usuários**
1. Logado como `operador_oto`, acesse `/acesso/usuarios/`.
   → **403** (sem permissão). O menu "Usuários" não aparece para ele.

**Caso 4.1.5 — Gestor consulta ODS, mas não gerencia usuários nem edita inventário**
1. Logado como `gestor_oto`: abra `/ods/` → **200**.
2. Abra `/acesso/usuarios/` → **403**; abra `/inventario/novo/` → **403**.

**Caso 4.1.6 — Admin gerencia usuários**
1. Logado como `admin_oto`, abra `/acesso/usuarios/` → lista.
2. Crie um usuário novo em `/acesso/usuarios/novo/` (perfil operador, ativo).
   → Aparece na lista.

**Caso 4.1.7 — Usuário inativo não entra**
1. Como admin, edite um usuário e desmarque **Ativo**. Faça logout.
2. Tente logar com esse usuário.
   → Login recusado.

### 4.2 BDP02 — Cadastrar item do Inventário

**Caso 4.2.1 — Cadastro válido**
1. Como `operador_oto`, abra `/inventario/novo/`.
2. Preencha **Nome** (obrigatório), marque um ou mais **Segmentos**, salve.
   → Vai para o detalhe do item; o item aparece em `/inventario/` e é encontrável por nome.

**Caso 4.2.2 — Cadastro sem obrigatório**
1. Em `/inventario/novo/`, deixe **Nome** vazio e salve.
   → Formulário recusado com erro no campo Nome; nenhum item é criado.

### 4.3 BDP04 — Consultar e filtrar

**Caso 4.3.1 — Filtro por nome + categoria**
1. Como `operador_oto`, em `/inventario/` digite parte do nome e escolha um **Segmento**; filtre.
   → Lista apenas os itens que casam com os dois filtros.

**Caso 4.3.2 — Limpar filtros**
1. Clique em **Limpar**.
   → Mostra todos os itens ativos.

**Caso 4.3.3 — Incluir inativos**
1. Marque **Incluir inativos** e filtre.
   → A lista passa a mostrar também itens inativos.

### 4.4 BDP03 — Editar com histórico

**Caso 4.4.1 — Edição registra histórico**
1. Abra um item, clique **Editar**, mude o **Nome** (ex.: A → B), salve.
2. Abra o detalhe → seção **Histórico de alterações**.
   → Mostra uma linha com campo=nome, valor anterior=A, valor novo=B, usuário e data/hora.
   Os demais campos permanecem inalterados.

### 4.5 BDP05 — Inativar (soft delete)

**Caso 4.5.1 — Inativar preserva histórico**
1. No detalhe de um item ativo, clique **Inativar**.
   → Status vira "Inativo"; some da listagem padrão de `/inventario/`.
2. Abra o detalhe direto (`/inventario/<id>/`).
   → Continua acessível, status Inativo, histórico preservado, e há registro de inativação
   com usuário e data/hora. Botão **Reativar** disponível.

### 4.6 BDP01 / BDP11 — Importação genérica com prévia

Crie um arquivo de exemplo (2 válidos, 1 duplicado, 1 sem obrigatório):
```bash
cat > /tmp/inventario_exemplo.csv <<'EOF'
nome,bairro,latitude,longitude
Hotel Exemplo A,Centro,-22.84,-48.91
Hotel Exemplo B,Jardim,,
Hotel Exemplo A,Centro,,
,Sem Nome,,
EOF
```

**Caso 4.6.1 — Prévia (BDP11: conferência sem gravar)**
1. Como `admin_oto`, abra `/importacao/`, selecione o arquivo, clique **Gerar prévia**.
   → Resumo: **4 lidos, 2 serão importados, 2 serão rejeitados**. Tabela de rejeitadas
   mostra linha + tipo (Duplicidade / Campo obrigatório) + motivo. **Nada gravado ainda.**

**Caso 4.6.2 — Confirmar (BDP01: grava uma única vez)**
1. Na prévia, clique **Confirmar importação (2)**.
   → Resultado: 2 importados, 2 rejeitados. Em `/inventario/`, cada "Hotel Exemplo" aparece
   **uma única vez** (duplicado não entra).

**Caso 4.6.3 — Cancelar**
1. Gere outra prévia e clique **Cancelar**.
   → Volta ao formulário; nada é gravado.

**Caso 4.6.4 — Separador `;` e coordenadas inválidas**
- Um CSV com `;` como separador é aceito.
- Uma linha com latitude fora de [-90,90] (ex.: `200`) é rejeitada por formato.

### 4.7 BDP01 — Importação da planilha oficial (INVENTARIO OFICIAL OLIMPIA)

A planilha oficial tem uma aba por categoria, com banner e linha de cabeçalho variável.
Exporte **uma aba** (ex.: Meios de Hospedagem) como CSV/XLSX. Exemplo de arquivo:
```bash
cat > /tmp/mh_oficial.csv <<'EOF'
INVENTARIO MEIOS DE HOSPEDAGEM,,,,,
,,,,,
,,,,,
QTD,NOME FANTASIA,RAZAO SOCIAL,CNPJ,ENDERECO,BAIRRO
0,TOTAL,,,,
1,Hotel Oficial A,A Ltda,12345678000199,Rua 1,Centro
2,Hotel Oficial B,B ME,98765432000111,Rua 2,Jardim
EOF
```

**Caso 4.7.1 — Importar aba oficial**
1. Como `admin_oto`, abra `/importacao/oficial/`.
2. Informe o **Segmento** (ex.: `Meios de Hospedagem`) e selecione o arquivo; importe.
   → Resumo: 2 criados, 0 atualizados, 0 ignorados. A linha **TOTAL é ignorada**.
   O CNPJ é detectado (tipo_documento = CNPJ), e cada item é vinculado ao segmento.
   Colunas comuns viram campos-base; demais colunas viram **campos específicos do segmento**;
   telefone/e-mail/site viram **contatos**; CADASTUR e CNAE vão para suas tabelas.

**Caso 4.7.2 — Reimportar é idempotente**
1. Importe o mesmo arquivo de novo.
   → 0 criados (itens já existem); não duplica.

### 4.8 Relatórios visuais

**Caso 4.8.1**
1. Abra `/inventario/relatorios/`.
   → Tiles de total/ativos/inativos/segmentos; barra de distribuição por status;
   gráfico de barras de itens por segmento (total e ativos por segmento).

### 4.9 Módulo ODS (BDP08/09/10/12)

**Caso 4.9.1 — BDP08 cadastrar indicador (nome obrigatório)**
1. Como `gestor_oto`, abra `/ods/novo/`. Salvar sem nome → recusado.
2. Com nome, descrição e meta → salvo e visível no detalhe.

**Caso 4.9.2 — BDP09 registrar dado de pesquisa (indicador obrigatório)**
1. `/ods/dados-pesquisa/novo/`: sem indicador → recusado; com indicador/data/valor → salvo
   e aparece no detalhe do indicador correto (e não em outro).

**Caso 4.9.3 — BDP10 regra de cálculo**
1. Crie um indicador com regra "Contar itens ativos com campo = valor"
   (ex.: campo `sustentabilidade`, valor `Sim`), vincule itens, clique **Calcular medição**.
   → Conta apenas itens **ativos** que atendem à regra; recalcular reflete mudanças.

**Caso 4.9.4 — BDP12 histórico ordenado**
1. No detalhe do indicador, veja **Histórico de medições**.
   → Datas em ordem crescente (mais antiga → mais recente).

### 4.10 Saúde e admin

- `/health/` → `{"status": "ok"}` (público, sem login).
- `/admin/` (como `admin_oto`) → administração completa em PT-BR de todas as tabelas.

---

## 5. Testes automatizados

### 5.1 Como rodar

```bash
cd /Users/enzopagotto/BdOplimpia
.venv/bin/python manage.py test              # tudo (54 testes)
.venv/bin/python manage.py test -v 2         # verboso (lista cada teste)
.venv/bin/python manage.py test acesso       # só um app
.venv/bin/python manage.py test inventario.tests.CadastroItemTests          # uma classe
.venv/bin/python manage.py test importacao.tests.ImportacaoBDP01Tests.test_importa_2_rejeita_2_e_resumo  # um teste
```

Os testes criam um banco **temporário** próprio; não afetam `db.sqlite3` nem os dados do seed.

### 5.2 O que a CI roda (replique localmente)

```bash
.venv/bin/python manage.py check             # valida a configuração do projeto
.venv/bin/python manage.py test              # roda a suíte
```

Definido em `.github/workflows/ci.yml` (push e pull request). Em push na `main` com testes
verdes, a CI também gera um pacote `.tar.gz` do código como artefato.

### 5.3 O que os testes cobrem (54 testes)

**acesso/tests.py — BDP13 (8 testes)**
- `test_credenciais_validas_permitem_entrar` — login com credenciais corretas.
- `test_credenciais_invalidas_sao_recusadas` — login recusado com senha errada.
- `test_logout_encerra_acesso` — após logout, rota protegida redireciona ao login.
- `test_admin_gerencia_usuarios` — administrador acessa gestão de usuários.
- `test_operador_edita_inventario_sem_gerenciar_usuarios` — operador: 200 no cadastro, 403 em usuários.
- `test_gestor_consulta_indicadores_sem_gerenciar_usuarios` — gestor: 200 em ODS, 403 em usuários.
- `test_gestor_nao_edita_inventario` — gestor recebe 403 no cadastro de item.
- `test_usuario_inativo_nao_entra` — usuário com `ativo=False` não loga.

**inventario/tests.py — BDP02/03/04/05 + modelo + relatórios (13 testes)**
- `test_cadastro_com_obrigatorios_salva_e_encontra_por_nome` — BDP02 cadastro válido.
- `test_cadastro_sem_obrigatorio_e_recusado_sem_criar_registro` — BDP02 recusa sem nome.
- `test_edicao_atualiza_consulta_e_registra_historico` — BDP03 edição + auditoria.
- `test_edicao_mantem_demais_campos` — BDP03 não altera campos não tocados.
- `test_filtro_categoria_e_nome_retorna_somente_um` — BDP04 filtro combinado.
- `test_sem_filtros_retorna_os_tres` — BDP04 sem filtro mostra todos.
- `test_inativar_some_da_listagem_padrao_mas_mantem_historico` — BDP05 soft delete.
- `test_listagem_pode_incluir_inativos` — BDP05 opção de incluir inativos.
- `test_latitude_fora_da_faixa_viola_constraint` — constraint de latitude.
- `test_preenchimento_exige_item_vinculado_ao_segmento` — regra do Preenchimento.
- `test_preenchimento_valido_quando_item_vinculado` — caminho válido do Preenchimento.
- `test_relatorios_agrega_por_status_e_segmento` — relatórios agregam corretamente.
- `test_relatorios_exige_login` — relatórios exigem autenticação.

**inventario/tests_xor.py — restrições Contato/Cadastur (5 testes)**
- `test_contato_com_ambos_e_invalido_no_clean` — contato com item E profissional é inválido.
- `test_contato_sem_nenhum_e_invalido_no_clean` — contato sem nenhum dos dois é inválido.
- `test_contato_com_ambos_viola_constraint_no_banco` — a mesma regra no nível do banco.
- `test_contato_apenas_item_valido` — contato só com item é válido.
- `test_cadastur_apenas_profissional_valido` — cadastur só com profissional é válido.

**importacao/tests.py — BDP01/BDP11 + fluxo de prévia (14 testes)**
- `test_resumo_4_verificados_2_validos_2_inconsistencias` — BDP11 resumo da validação.
- `test_cada_inconsistencia_tem_linha_tipo_e_motivo` — BDP11 detalhe de cada inconsistência.
- `test_status_com_inconsistencias` — status da importação com inconsistências.
- `test_importa_2_rejeita_2_e_resumo` — BDP01 contagem 4/2/2.
- `test_validos_gravados_uma_unica_vez` — BDP01 não duplica válidos.
- `test_rejeicoes_identificam_linha_e_motivo` — BDP01 motivos (duplicado/obrigatório).
- `test_duplicidade_contra_base_existente` — duplicidade também contra itens já no banco.
- `test_coordenada_invalida_e_rejeitada` — coordenada fora de faixa rejeitada.
- `test_separador_ponto_e_virgula` — aceita CSV com `;`.
- `test_importa_xlsx_classifica_corretamente` — importação de XLSX (openpyxl).
- `test_upload_gera_previa_sem_gravar` — upload gera prévia e não grava.
- `test_confirmar_grava_itens_aceitos` — confirmação grava os aceitos.
- `test_confirmar_sem_previa_redireciona` — confirmar sem prévia pendente redireciona.
- `test_cancelar_descarta_previa` — cancelar descarta a prévia.

**importacao/tests_oficial.py — formato da planilha oficial (7 testes)**
- `test_detecta_linha_de_cabecalho` — acha a linha de cabeçalho real entre banners.
- `test_interpreta_itens_base_contato_coordenadas_e_campos` — mapeia base, contato, coords, campos.
- `test_persistir_cria_itens_vinculos_campos_e_contatos` — grava item + segmento + campos + contato.
- `test_persistir_e_idempotente` — reimportar não duplica.
- `test_ignora_linhas_de_total` — linhas TOTAL/TOTAIS não viram itens.
- `test_persistir_so_grava_item_valido` — só grava o item real.
- `test_importa_aba_oficial` — fluxo completo pela view `/importacao/oficial/`.

**ods/tests.py — BDP08/09/10/12 (6 testes)**
- `test_cadastro_salva_nome_descricao_meta` — BDP08 cadastro salva os campos.
- `test_cadastro_sem_nome_e_recusado` — BDP08 recusa sem nome.
- `test_registra_dados_e_aparecem_no_indicador_certo` — BDP09 dado no indicador correto.
- `test_dado_sem_indicador_e_recusado` — BDP09 recusa sem indicador.
- `test_conta_itens_ativos_com_campo_sustentabilidade_sim` — BDP10 regra de cálculo.
- `test_historico_ordenado_da_mais_antiga_a_mais_recente` — BDP12 ordenação do histórico.

**oto/tests.py — infraestrutura (1 teste)**
- `test_health_endpoint_responds` — `/health/` responde `{"status": "ok"}`.

### 5.4 Matriz história → testes

| História | Prioridade | Testes automatizados | Caso manual |
|---|---|---|---|
| BDP01 Importar inventário | Must | importacao: importa_2_rejeita_2, validos_gravados_uma_unica_vez, rejeicoes_identificam, previa/confirmar; oficial: todos | 4.6, 4.7 |
| BDP11 Validar integridade | Must | importacao: resumo_4_2_2, cada_inconsistencia, status_com_inconsistencias | 4.6.1 |
| BDP02 Cadastrar item | Must | inventario: cadastro_com_obrigatorios, cadastro_sem_obrigatorio | 4.2 |
| BDP03 Editar com histórico | Must | inventario: edicao_registra_historico, edicao_mantem_demais | 4.4 |
| BDP04 Consultar/filtrar | Must | inventario: filtro_categoria_e_nome, sem_filtros | 4.3 |
| BDP13 Autenticação/permissões | Must | acesso: 8 testes | 4.1 |
| BDP05 Inativar | Should | inventario: inativar_some, listagem_inclui_inativos | 4.5 |
| BDP08 Cadastrar indicador | Could | ods: cadastro_salva, cadastro_sem_nome | 4.9.1 |
| BDP09 Dados de pesquisa | Could | ods: registra_dados, dado_sem_indicador | 4.9.2 |
| BDP10 Regra de cálculo | Could | ods: conta_itens_ativos | 4.9.3 |
| BDP12 Histórico indicador | Could | ods: historico_ordenado | 4.9.4 |

---

## 6. Verificações de apoio (smoke tests sem navegador)

Com o servidor rodando (`runserver`), estes comandos confirmam o básico via terminal:

```bash
# Saúde (público)
curl -s -w "\n%{http_code}\n" http://127.0.0.1:8000/health/

# Painel sem login deve redirecionar (302)
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/
```

Para testar fluxos autenticados via curl é preciso capturar o cookie CSRF e de sessão;
na prática, os **testes automatizados** (seção 5) já cobrem esses fluxos de ponta a ponta.

---

## 7. Solução de problemas

| Sintoma | Causa provável | Ação |
|---|---|---|
| `no such table` ao abrir páginas | migrations não aplicadas | `.venv/bin/python manage.py migrate` |
| Login não funciona após trocar modelo de usuário | banco antigo | `rm -f db.sqlite3 && migrate && seed_demo` |
| XLSX não importa | openpyxl ausente | `.venv/bin/python -m pip install -r requirements.txt` |
| `403` em páginas | perfil sem permissão (esperado) | use um usuário com o perfil correto |
| Porta 8000 ocupada | servidor anterior ativo | `pkill -f "manage.py runserver"` ou use outra porta |

---

## 8. Referências

- `_docs/00_SPEC_consolidada.md` — histórias, critérios de aceitação e regras de negócio.
- `_docs/01_modelo_logico.md` — modelo lógico relacional (tabelas, FKs, restrições).
- `_docs/02_planilha_oficial.md` — estrutura real da planilha INVENTARIO OFICIAL OLIMPIA.
- `README.md` — visão geral, módulos e execução resumida.
