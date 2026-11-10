# Observatório de Turismo de Olímpia

Sistema web para integrar o Inventário Turístico, registros de ISSQN e indicadores ODS.

## Tecnologias

- Python 3.12 e Django 5.2
- PostgreSQL para a base do projeto
- SQLite para verificações locais e integração contínua sem dependências externas
- GitHub Actions para integração contínua

## Executar localmente

```bash
python -m venv .venv
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

No Windows, ative `.venv` e use o `python` desse ambiente antes de instalar as dependências.
A aplicação disponibiliza `/admin/` e `/health/` nesta estrutura inicial.

O protótipo navegável de baixa fidelidade está em
[`docs/prototipo-baixa-fidelidade/index.html`](docs/prototipo-baixa-fidelidade/index.html).
Abra o arquivo no navegador para revisar os fluxos antes da implementação.

Para usar PostgreSQL, configure `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`,
`POSTGRES_HOST` e `POSTGRES_PORT` no ambiente. Configure também `DJANGO_SECRET_KEY`
antes de disponibilizar o sistema fora do ambiente local.

## Integração contínua

O workflow em `.github/workflows/ci.yml` roda em cada push e pull request.
Ele instala as dependências, executa `manage.py check` e os testes do projeto.
Novos módulos devem incluir testes para que entrem nessa verificação.
Quando a alteração chega à branch `main` com os testes aprovados, o workflow
gera um pacote de código como artefato da execução.

A implantação automatizada dependerá da definição do ambiente de hospedagem
e do responsável pela operação do sistema.
