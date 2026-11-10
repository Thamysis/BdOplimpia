# OTO — Base de Dados Principal — Especificação Consolidada

Fonte: Google Drive (Observatório de Turismo de Olímpia), diagramas drawio (MER, Modelo Lógico,
Arquitetura, Casos de Uso) + Planilha de Requisitos de Teste (histórias BDP + critérios de aceitação)
+ Matriz de Rastreabilidade.

## Escopo
Estamos implementando **apenas a "BASE DE DADOS PRINCIPAL"** e os módulos ligados a ela no backend
Django 5.2 + PostgreSQL. Núcleo = Inventário Turístico. Módulos de suporte: Importação/Validação,
Auditoria, Acesso/Permissões. Módulo ODS é complementar (Could).

## Perfis de usuário
- **Administrador**: gerencia usuários/permissões; importa inventário; tudo do operador.
- **Operador de dados**: cadastra/edita/consulta/inativa itens do inventário; registra dados de pesquisa.
- **Gestor do OTO**: consulta indicadores ODS e histórico; cadastra indicadores ODS; não gerencia usuários.

## Histórias de usuário (backlog priorizado) + critérios de aceitação

### Must (núcleo)
- **BDP01 — Importar Inventário** (Base de Dados Principal): administrador importa dados do Inventário
  para base relacional e confere consistência de cada carga.
  *Critério:* arquivo com 2 válidos, 1 duplicado, 1 sem campo obrigatório → importa válidos 1x, aponta
  linha+motivo das rejeições, apresenta **4 lidos, 2 importados, 2 rejeitados**.
- **BDP11 — Verificar integridade da importação** (Base de Dados Principal): resumo de divergências e
  duplicidades antes de usar os dados.
  *Critério:* carga com 2 válidos/1 duplicado/1 sem obrigatório → **4 verificados, 2 válidos, 2
  inconsistências**; cada inconsistência traz linha, tipo e motivo; nenhum inválido entra na base.
- **BDP02 — Cadastrar item** (Inventário): salvar novo estabelecimento/atrativo; encontrável por nome.
  *Critério:* campos obrigatórios preenchidos → salvo e localizado por nome; omitir obrigatório →
  recusado com indicação do campo, nenhum registro criado.
- **BDP03 — Editar item** (Inventário): manter atualizado + histórico.
  *Critério:* alterar nome A→B; consulta mostra B; histórico registra A, B, usuário e data/hora;
  demais campos inalterados.
- **BDP04 — Consultar/filtrar itens** (Inventário).
  *Critério:* 3 itens ativos (Hotel A, Hotel B em Hospedagem; Restaurante C em Alimentação);
  filtrar categoria=Hospedagem e nome=Hotel A → só Hotel A; limpar filtros → os três.
- **BDP13 — Autenticação e permissões**: perfis administrador/operador/gestor.
  *Critério:* credenciais válidas entram, inválidas recusadas; admin gerencia permissões; operador
  edita inventário sem gerenciar usuários; gestor consulta indicadores sem gerenciar usuários;
  logout encerra acesso.

### Should
- **BDP05 — Inativar item (soft delete)** (Inventário): sem apagar histórico.
  *Critério:* item ativo com histórico → após inativar some da listagem padrão; consulta direta mostra
  status Inativo e mantém histórico; ação registra usuário e data/hora.

### Could (Módulo ODS — complementar)
- **BDP08 — Cadastrar indicador ODS**: nome, descrição, meta. Sem nome → recusado.
- **BDP09 — Registrar dados de pesquisa**: indicador, data_referencia, valor. Sem indicador → recusado.
- **BDP10 — Relacionar inventário a indicadores + regra de cálculo documentada**.
  *Critério:* regra "contar itens ativos com campo sustentabilidade=Sim"; 1 ativo + 1 inativo com esse
  valor → resultado 1; vínculo consultável; recálculo reflete alterações.
- **BDP12 — Consultar histórico de indicador**: medições ordenadas por data (asc).

## Regras de negócio
- **RN01**: inativar sem excluir fisicamente (soft delete).
- **RN03 / RF15**: rastrear responsável, data e alterações (auditoria com valor anterior/novo).
- Contato: exatamente um entre id_item e id_profissional preenchido.
- Cadastur: exatamente um entre id_item e id_profissional preenchido.
- Item_Inventario: latitude ∈ [-90, 90], longitude ∈ [-180, 180] quando informadas.
- Preenchimento: (id_item, id_campo) é chave composta; o campo deve pertencer a um segmento ao qual o
  item esteja vinculado em Participa.

## Rastreabilidade (requisito do plano → história)
- RF01 Gestão e Migração de Dados → BDP01, BDP11 (Must)
- RF02 Painel Administrativo → BDP02, BDP03, BDP04 (Must), BDP05 (Should)
- RF03 Pesquisas e ODS (opcional) → BDP08, BDP09, BDP10, BDP12 (Could)
- RF04 Autenticação e controle de acesso → BDP13 (Must)

## Tecnologias / Arquitetura
Python 3.12 + Django 5.2; PostgreSQL (SQLite para testes/CI). Camadas: Apresentação (frontend web) /
Aplicação-API (Django, módulos) / Acesso a dados (repositórios) / PostgreSQL. Módulos backend:
Inventário Turístico, Importação e Validação, Auditoria, Acesso/Permissões, ODS (complementar).
