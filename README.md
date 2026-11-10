# Observatório de Turismo de Olímpia — Base de Dados Principal

Sistema web para centralizar o **Inventário Turístico** de Olímpia em uma base de dados
relacional, substituindo as planilhas atuais, com importação assistida, auditoria de
alterações, controle de acesso por perfil e um módulo complementar de indicadores ODS.

## Tecnologias

- Python 3.12 e Django 5.2
- PostgreSQL para a base do projeto
- SQLite para verificações locais e integração contínua sem dependências externas
- GitHub Actions para integração contínua

## Módulos (apps Django)

- **acesso** — usuário customizado com perfis (administrador, operador, gestor),
  autenticação e autorização por perfil (BDP13).
- **inventario** — núcleo: segmentos, itens, campos por segmento, preenchimentos,
  profissionais, contatos, Cadastur, CNAE; cadastro, edição, consulta/filtro e
  inativação (soft delete) — BDP02, BDP03, BDP04, BDP05.
- **auditoria** — histórico de alterações dos itens (usuário, data/hora, campo,
  valores anterior e novo) — RN03 / RF15.
- **importacao** — importação e validação do Inventário (CSV/XLSX/ODS), com
  classificação de registros válidos/duplicados/inválidos e registro de
  inconsistências — BDP01, BDP11.
- **ods** — módulo complementar: indicadores, dados de pesquisa, regras de cálculo
  documentadas e histórico de medições — BDP08, BDP09, BDP10, BDP12.

## Perfis de acesso

| Perfil | Pode |
|--------|------|
| Administrador | Tudo, incluindo gerenciar usuários e importar dados |
| Operador de dados | Cadastrar/editar/consultar/inativar itens; registrar dados de pesquisa |
| Gestor do OTO | Consultar e cadastrar indicadores ODS e seu histórico |

## Executar localmente

```bash
python -m venv .venv
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo        # dados de demonstração (opcional)
python manage.py createsuperuser  # ou use as contas do seed_demo
python manage.py runserver
```

No Windows, ative `.venv` e use o `python` desse ambiente antes de instalar as dependências.

### Contas de demonstração (`seed_demo`)

Senha para todas: `demo12345`

- `admin_oto` (administrador) — também é superusuário do `/admin/`
- `operador_oto` (operador)
- `gestor_oto` (gestor)

### Rotas principais

- `/` — painel inicial
- `/acesso/login/`, `/acesso/logout/`, `/acesso/usuarios/`
- `/inventario/` — listagem/consulta; `/inventario/novo/`, `/inventario/<id>/`
- `/inventario/relatorios/` — relatórios visuais (distribuição por status e por segmento)
- `/importacao/` — importar com prévia (upload → prévia classificada → confirmar); `/importacao/historico/`
- `/ods/` — indicadores ODS
- `/admin/` — Django admin (PT-BR) e `/health/` — verificação de saúde

### Formato de importação

Arquivo CSV (vírgula ou ponto e vírgula), XLSX ou ODS. Coluna **`nome`** é obrigatória;
colunas opcionais: `razao_social, tipo_documento, documento, endereco, bairro,
latitude, longitude`. Linhas duplicadas (mesmo nome) ou sem campo obrigatório são
rejeitadas com o motivo; coordenadas fora das faixas válidas também. O envio gera
primeiro uma **prévia** com cada linha classificada como aceita ou rejeitada; nada é
gravado até a confirmação (BDP01), e a conferência de integridade/inconsistências
corresponde ao BDP11.

## Banco de dados

Por padrão usa SQLite (`db.sqlite3`). Para PostgreSQL, configure `POSTGRES_DB`,
`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST` e `POSTGRES_PORT` no ambiente.
Configure também `DJANGO_SECRET_KEY` antes de disponibilizar o sistema fora do ambiente
local. O modelo de dados segue o Modelo Lógico Relacional documentado em
[`_docs/01_modelo_logico.md`](_docs/01_modelo_logico.md); a especificação consolidada
das histórias e critérios de aceitação está em
[`_docs/00_SPEC_consolidada.md`](_docs/00_SPEC_consolidada.md).

## Testes

```bash
python manage.py test
```

Os testes cobrem os critérios de aceitação de cada história (BDP01–BDP13) e as
restrições de integridade do modelo. **Guia completo de execução e testes (passo a
passo, todos os casos, manual e automatizado):** [`_docs/03_GUIA_DE_TESTES.md`](_docs/03_GUIA_DE_TESTES.md).

## Integração contínua

O workflow em `.github/workflows/ci.yml` roda em cada push e pull request.
Ele instala as dependências, executa `manage.py check` e os testes do projeto.
Novos módulos devem incluir testes para que entrem nessa verificação.
Quando a alteração chega à branch `main` com os testes aprovados, o workflow
gera um pacote de código como artefato da execução.

O protótipo navegável de baixa fidelidade está em
[`docs/prototipo-baixa-fidelidade/index.html`](docs/prototipo-baixa-fidelidade/index.html).
