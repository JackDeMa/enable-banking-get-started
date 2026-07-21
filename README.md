# Enable Banking — get started

Questo repository è un piccolo ambiente di sviluppo per provare l'API AIS di
[Enable Banking](https://enablebanking.com/): elenca le banche disponibili,
avvia il consenso nel browser, riceve il callback OAuth tramite un backend
Django locale, conserva le sessioni complete in SQLite e interroga saldo e
transazioni.

> Il progetto è pensato per sviluppo e sperimentazione locale. Il backend usa
> `DEBUG=True`, una chiave Django di sviluppo e restituisce la sessione come
> JSON: non va esposto su Internet né usato così com'è in produzione.

## Cosa contiene la repo

La procedura seguente usa esclusivamente file versionati:

```text
src/enable_banking/                     client, JWT, configurazione e storage
web/                                    callback HTTPS Django
notebooks/02_enable_banking_plus_django.ipynb
                                        flusso consigliato con callback automatico
notebooks/01_enable_banking_get_started.ipynb
                                        vecchio esempio del flusso manuale
.env.example                            configurazione locale di esempio
pyproject.toml                          package e dipendenze opzionali
AGENTS.md                               istruzioni operative per agenti LLM
CLAUDE.md                               ingresso per Claude Code verso AGENTS.md
```

Il notebook `01_enable_banking_get_started.ipynb` è conservato come riferimento,
ma chiama il vecchio metodo manuale `create_new_session`, oggi disabilitato nel
client. Per un flusso completo usare il notebook `02` e il backend Django.

## Prerequisiti

- Python 3.11 o successivo;
- un'applicazione configurata nel pannello Enable Banking;
- la relativa chiave privata PEM;
- `mkcert` installato, per creare un certificato HTTPS locale attendibile.

Nel pannello Enable Banking associa prima la banca che vuoi usare e registra
esattamente questo redirect URL:

```text
https://localhost:8000/callback
```

## Installazione

Dalla root della repo crea un ambiente virtuale e installa package, backend,
notebook e strumenti di sviluppo:

```powershell
python -m venv .venv
./.venv/Scripts/Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev,web,notebook]"
```

Su macOS/Linux l'attivazione equivalente è `source .venv/bin/activate`.

## Configurazione

1. Copia il template locale:

   ```powershell
   Copy-Item .env.example .env
   ```

2. Copia la chiave privata nella root del progetto o indica un percorso
   assoluto. Il nome del file, senza `.pem`, deve coincidere con l'application
   ID Enable Banking: il client lo usa come `kid` del JWT.

3. Completa `.env`, per esempio:

   ```dotenv
   PEM_FILE=./00000000-0000-0000-0000-000000000000.pem
   SESSION_DB=data/enable_banking_sessions.sqlite3
   ```

I percorsi relativi sono risolti rispetto alla directory che contiene `.env`.
Non committare `.env`, chiavi PEM o dati di sessione.

## Certificato HTTPS locale

Il redirect configurato è HTTPS. Crea quindi una CA locale attendibile e il
certificato per `localhost`:

```powershell
New-Item -ItemType Directory -Force tls | Out-Null
mkcert -install
mkcert -cert-file tls/server.crt -key-file tls/server.key localhost 127.0.0.1 ::1
```

Su macOS/Linux sostituisci il primo comando con `mkdir -p tls`; i due comandi
`mkcert` restano uguali.

## Avvio e primo collegamento

Verifica la configurazione Django:

```powershell
python web/manage.py check
```

Avvia il callback server e lascialo in esecuzione:

```powershell
python -m uvicorn config.asgi:application `
  --app-dir web `
  --host 127.0.0.1 `
  --port 8000 `
  --reload `
  --ssl-certfile tls/server.crt `
  --ssl-keyfile tls/server.key
```

`--reload` riavvia automaticamente il backend quando cambia il codice. Se il
server era già attivo prima di un aggiornamento, riavvialo manualmente; allo
stesso modo, riavvia il kernel Jupyter per ricaricare i moduli Python già
importati.

In un secondo terminale, con lo stesso ambiente attivo, apri il notebook:

```powershell
python -m jupyter lab notebooks/02_enable_banking_plus_django.ipynb
```

Nel notebook:

1. esegui la prima cella per caricare configurazione e banche;
2. sostituisci `MyBank` con il nome della banca associata all'applicazione;
3. esegui `client.open_session(bank)`;
4. se non esiste una sessione riutilizzabile, apri l'URL stampato dal client e
   completa il consenso nel browser;
5. Enable Banking reindirizza a `/callback`; Django scambia il `code` con una
   sessione e salva l'intera risposta nel database SQLite locale;
6. riesegui la cella con `client.open_session(bank)`, quindi interroga saldo e
   transazioni.

Il client usa il primo account restituito dalla sessione. `open_session()`
restituisce `True` quando una sessione salvata è stata caricata e `False` quando
ha appena avviato un nuovo consenso nel browser.

## Database delle sessioni

Il database configurato da `SESSION_DB` viene creato automaticamente al primo
accesso; non servono migration. La tabella `enable_banking_sessions` contiene:

- una chiave numerica locale;
- il `session_id` univoco;
- `bank_key`, nome e paese della banca, usati per trovare l'ultima sessione;
- `payload_json`, cioè l'intera risposta restituita da Enable Banking;
- date di creazione e ultimo aggiornamento.

Ogni nuovo `session_id` produce un record distinto, quindi rimane lo storico
delle autorizzazioni per banca. Se lo stesso callback viene elaborato di nuovo,
il record con quel `session_id` viene aggiornato senza creare duplicati. Il
client legge l'ultimo record della banca dal DB e usa il suo `session_id` per
richiedere a Enable Banking lo stato corrente della sessione.

I vecchi file `data/enable_banking_session.json` e
`data/enable_banking_session_from_django.json` non vengono più letti né
importati automaticamente. Possono essere conservati temporaneamente come
backup locale o eliminati manualmente dopo aver creato una nuova sessione.

Se `open_session()` segnala che la sessione non è disponibile, il messaggio
indica anche banca e percorso del database consultato. Controlla innanzitutto
che callback server e kernel Jupyter siano stati riavviati dopo l'aggiornamento:
un vecchio processo continua a scrivere nei precedenti file JSON.

## File locali che compariranno

Questi file o directory non sono versionati e possono apparire durante setup ed
esecuzione:

| Percorso | Origine e contenuto |
| --- | --- |
| `.venv/` | ambiente virtuale e dipendenze installate |
| `.env` | configurazione locale e percorso della chiave privata |
| `*.pem` | chiave privata Enable Banking |
| `tls/server.crt`, `tls/server.key` | certificato e chiave HTTPS creati con `mkcert` |
| `data/enable_banking_sessions.sqlite3` | database con un record e il payload completo per ogni sessione |
| `data/enable_banking_sessions.sqlite3-journal` | eventuale file transitorio creato da SQLite durante una scrittura |
| `web/db.sqlite3` | database Django, se vengono eseguite le migration |
| `*.egg-info/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/` | artefatti di installazione, Python e tool |
| `.ipynb_checkpoints/` | checkpoint locali di Jupyter |

Sono tutti ignorati da Git. Il database delle sessioni e la risposta mostrata
dal callback possono contenere dati bancari o token: trattali come segreti e
eliminali quando non servono più.

## Verifiche locali

```powershell
python -m ruff check src web
python -m pytest
python web/manage.py check
```

I test dello storage usano soltanto sessioni sintetiche e database temporanei.
