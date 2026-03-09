# Monitor Fiscal NCM

Monitor de alteracoes estruturais de NCM e atos do DOU, com historico em SQLite, deduplicacao por ato e alertas opcionais.

## Execucao

```powershell
python -m pip install -r requirements.txt
copy .env.example .env
python monitor_fiscal.py
```

## Dashboard

```powershell
streamlit run dashboard.py
```

## App NCM unica

```powershell
python -m streamlit run app_ncm_unica.py
```

No app de NCM unica:
1. Digite uma ou mais NCMs (8 digitos), separadas por virgula.
2. Clique em `Consultar sites agora`.
3. O app consulta o DOU online (sem usar historico do banco), dia a dia em ordem decrescente, ate encontrar as ultimas alteracoes.
4. Veja data, tipo de alteracao, titulo, detalhe e URL do ato.
5. O app exibe o build atual (`versao + revisao`) para facilitar validacao de deploy.
6. A cada consulta, o app salva snapshot em `snapshots/live_ncm` e compara automaticamente com o ultimo snapshot da mesma NCM.

## Versao do app

Arquivo de versao: `VERSION`

Opcionalmente, voce pode sobrescrever em runtime com variavel de ambiente:

```env
APP_VERSION=1.0.1
```

## O que monitora

1. Estrutural (RFB): compara snapshots filtrados pelas NCMs de `ncms.csv` e registra `NOVA`, `REMOVIDA`, `DESCRICAO_ALTERADA`, `NAO_ENCONTRADA`.
2. DOU: busca por termos configuraveis, pagina resultados, abre atos completos e registra evento apenas quando uma NCM monitorada aparece no texto.

## Banco

Arquivo: `database.db`

Tabelas principais:

1. `historico_alteracoes`
2. `dou_atos_processados`
3. `execucoes`

## Alertas

Ative no `.env`:

```env
ENABLE_ALERTS=true
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...

SMTP_HOST=smtp.seudominio.com
SMTP_PORT=587
SMTP_USER=...
SMTP_PASSWORD=...
SMTP_FROM=monitor@dominio.com
SMTP_TO=destino@dominio.com
```

Mesmo sem SMTP configurado, quando houver alertas o app grava um preview do email em:
`logs/email_outbox/email_preview_YYYYMMDD_HHMMSS.txt`

## Operacao

Backup:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\backup_db.ps1 -ProjectDir .
```

Agendamento diario (Windows Task Scheduler):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\register_task.ps1 -ProjectDir . -PythonExe python -DailyAt 08:00
```

## Docker

```powershell
docker compose up --build monitor
docker compose up --build dashboard
```

## Testes

```powershell
python -m unittest discover -s tests -v
```
