# Agente de Triagem de E-mails

Agente automatizado que coleta e-mails do Gmail, analisa cada um com LLM (GPT-4o-mini), filtra os resultados e envia um digest diário via WhatsApp. Projeto com fins educativos, construído com **LangChain** e **LangGraph**.

---

## Visão geral

O agente executa de forma autônoma em um horário configurável (padrão: todos os dias às 7h). Em cada execução, ele:

1. Coleta os e-mails recebidos desde a última execução bem-sucedida
2. Analisa cada e-mail com um LLM para classificar prioridade, categoria e necessidade de ação
3. Filtra os resultados conforme regras configuráveis
4. Formata e envia um digest via WhatsApp, com fallback para e-mail SMTP

---

## Arquitetura

O agente é implementado como um **LangGraph StateGraph** com 9 nós executados em sequência, com ramificações condicionais para retry e roteamento por prioridade.

```
[Gatilho]
    │
    ▼
Nó 1: Coleta Gmail
    │  (lê last_run.json para janela de coleta)
    ▼
Nó 2: Chunking
    │  (divide em lotes de CHUNK_SIZE)
    ▼
Nó 3: Análise LLM ◄─────────────────────┐
    │  (GPT-4o-mini + JsonOutputParser)  │
    ▼                                    │ retry (chunk de 1)
Nó 4: Validação de qualidade ────────────┘
    │  (valida campos, confidence, priority)
    ▼
Nó 5: Filtro + Roteador
    ├── (sem e-mails relevantes) ──────────────────────────────────────┐
    └── (com e-mails relevantes)                                       │
          │                                                            │
          ▼                                                            │
    Nó 6a: Alerta imediato (e-mails CRITICAL)                         │
          │                                                            │
          ▼                                                            │
    Nó 6b: Formata digest                                             │
          │  (emojis, ordenação por prioridade, quebra por limite)    │
          ▼                                                            │
    Nó 7: Sumarização do dia (LLM)                                    │
          │                                                            │
          └──────────────────────────────────────────────────────────►│
                                                                       ▼
                                                               Nó 8: Envio
                                                                 (WhatsApp → SMTP fallback)
                                                                 grava last_run.json
```

### Estado compartilhado (`EmailAgentState`)

Todos os nós leem e escrevem em um `TypedDict` compartilhado que percorre o grafo:

| Campo | Tipo | Descrição |
|---|---|---|
| `raw_emails` | `list[dict]` | E-mails brutos coletados do Gmail |
| `chunks` | `list[list[dict]]` | Lotes para análise LLM (e retries) |
| `analyzed_emails` | `list[dict]` | JSONs analisados pelo LLM |
| `invalid_emails` | `list[dict]` | E-mails que esgotaram retries |
| `filtered_emails` | `list[dict]` | E-mails após filtros configuráveis |
| `critical_emails` | `list[dict]` | Subconjunto com `priority == CRITICAL` |
| `digest_messages` | `list[str]` | Mensagens formatadas para envio |
| `summary` | `str` | Frase de contexto do dia (gerada pelo LLM) |
| `retry_counts` | `dict[str, int]` | Contador de retries por `message_id` |
| `errors` | `list[str]` | Erros não fatais registrados na execução |

---

## Stack tecnológica

| Componente | Tecnologia |
|---|---|
| Linguagem | Python 3.11+ |
| Orquestração do agente | LangGraph (StateGraph) |
| Chain de análise | LangChain |
| LLM | OpenAI GPT-4o-mini (configurável) |
| Coleta de e-mails | Gmail API (OAuth2) |
| Envio WhatsApp | Evolution API (via Docker) |
| Fallback de notificação | SMTP (Gmail App Password) |
| Agendamento | APScheduler |
| Configuração | Variáveis de ambiente (`.env`) |
| Gerenciador de pacotes | uv |

---

## Pré-requisitos

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) — `pip install uv`
- Docker (Engine ou Desktop) com suporte a `docker compose`
- Conta Google com Gmail API habilitada
- Chave de API da OpenAI
- WhatsApp configurado via Evolution API

---

## Instalação

### 1. Clonar o repositório

```bash
git clone <url-do-repositorio>
cd AutoVerifEmail_Langchain
```

### 2. Instalar dependências

```bash
uv sync
```

Isso cria automaticamente o `.venv` com todos os pacotes necessários.

### 3. Configurar variáveis de ambiente

```bash
cp .env.example .env   # Linux/macOS
copy .env.example .env  # Windows
```

Edite o arquivo `.env` preenchendo todos os valores conforme as seções abaixo.

---

## Configuração

### Variáveis de ambiente

| Variável | Descrição | Padrão |
|---|---|---|
| `OPENAI_API_KEY` | Chave da API da OpenAI | — |
| `LLM_MODEL` | Modelo OpenAI a ser usado | `gpt-4o-mini` |
| `GMAIL_CREDENTIALS_PATH` | Caminho para o `credentials.json` do Google | `credentials.json` |
| `GMAIL_TOKEN_PATH` | Caminho para o `token.json` gerado no primeiro login | `token.json` |
| `EMAIL_BODY_MAX_CHARS` | Limite de caracteres do corpo do e-mail enviado ao LLM | `3000` |
| `CHUNK_SIZE` | Quantidade de e-mails por lote de análise | `10` |
| `MIN_CONFIDENCE` | Confiança mínima aceita na análise LLM (0–1) | `0.5` |
| `MAX_RETRIES` | Máximo de tentativas de reanálise por e-mail inválido | `2` |
| `FILTER_CATEGORIES` | Categorias a **excluir** do digest (separadas por vírgula) | `SPAM,MARKETING` |
| `FILTER_MIN_PRIORITY` | Prioridade mínima para incluir (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) | `LOW` |
| `FILTER_REQUIRES_ACTION` | Se `true`, inclui apenas e-mails que requerem ação | `false` |
| `FILTER_REQUIRES_RESPONSE` | Se `true`, inclui apenas e-mails que requerem resposta | `false` |
| `SCHEDULE_CRON` | Expressão cron do agendamento (5 campos) | `0 7 * * *` |
| `SCHEDULE_TIMEZONE` | Fuso horário do agendamento | `America/Sao_Paulo` |
| `COLLECTION_WINDOW_HOURS` | Janela de coleta usada apenas na **primeira execução** | `24` |
| `EVOLUTION_URL` | URL da Evolution API | `http://localhost:8080` |
| `EVOLUTION_API_KEY` | Chave de API da Evolution API | — |
| `EVOLUTION_INSTANCE` | Nome da instância WhatsApp criada na Evolution API | — |
| `WHATSAPP_TARGET_NUMBER` | Número de destino das mensagens (ex: `5511999999999`) | — |
| `WHATSAPP_MAX_CHARS` | Limite de caracteres por mensagem WhatsApp | `4096` |
| `SMTP_HOST` | Servidor SMTP (fallback) | `smtp.gmail.com` |
| `SMTP_PORT` | Porta SMTP | `587` |
| `SMTP_USER` | E-mail do remetente SMTP | — |
| `SMTP_PASSWORD` | Senha de app do Gmail (não a senha normal da conta) | — |
| `FALLBACK_EMAIL_TO` | E-mail de destino do fallback SMTP | — |

---

### Gmail API — `credentials.json`

1. Acesse o [Google Cloud Console](https://console.cloud.google.com)
2. Crie ou selecione um projeto
3. **APIs e Serviços → Biblioteca** → ative a **Gmail API**
4. **APIs e Serviços → Tela de consentimento OAuth** → tipo **Externo** → adicione seu e-mail como **usuário de teste**
5. **Credenciais → Criar credenciais → ID do cliente OAuth** → tipo **Aplicativo de computador**
6. Baixe o JSON gerado e salve como `credentials.json` na raiz do projeto

> Na **primeira execução**, o navegador abrirá para autorização OAuth2. O arquivo `token.json` será gerado automaticamente e reutilizado nas execuções seguintes.

---

### Evolution API (WhatsApp)

```bash
# Suba os containers conforme o docker-compose.yml da Evolution API
docker compose up -d

# Acesse o painel em http://localhost:8080/manager
# Crie uma instância, conecte o WhatsApp via QR Code
# e preencha EVOLUTION_INSTANCE e EVOLUTION_API_KEY no .env
```

> **Atenção:** no `docker-compose.yml` da Evolution API, certifique-se de que `CACHE_REDIS_URI` usa o nome do serviço Redis (ex: `redis://evolution_redis:6379/...`) e **não** `localhost`, pois dentro do container `localhost` aponta para o próprio container.

---

### SMTP — Senha de App do Gmail

1. Na conta Google: **Segurança → Verificação em 2 etapas** (deve estar ativa)
2. **Senhas de app** → gere uma para "Outro" → copie os 16 dígitos
3. Use como valor de `SMTP_PASSWORD` no `.env`

---

### Validar o ambiente

```bash
# Linux/macOS
.venv/bin/python check_env.py

# Windows
.venv\Scripts\python.exe check_env.py
```

---

## Executando o agente

### Execução imediata (manual)

```bash
# Linux/macOS
.venv/bin/python main.py --run-now

# Windows
.venv\Scripts\python.exe main.py --run-now
```

### Agendamento automático

```bash
# Linux/macOS
.venv/bin/python main.py

# Windows
.venv\Scripts\python.exe main.py
```

O processo fica em execução contínua e dispara conforme o `SCHEDULE_CRON` configurado no `.env`.

---

## Resetar o histórico

O arquivo `last_run.json` armazena o timestamp da última execução bem-sucedida e controla a janela de coleta do Gmail.

```bash
# Reprocessar as últimas COLLECTION_WINDOW_HOURS horas
rm last_run.json         # Linux/macOS
del last_run.json        # Windows

# Reprocessar a partir de uma data específica:
# edite last_run.json manualmente antes de executar
# {"last_run": "2026-06-01T00:00:00+00:00"}
```

---

## Estrutura do projeto

```
AutoVerifEmail_Langchain/
├── main.py                    # Ponto de entrada + agendamento (APScheduler)
├── check_env.py               # Validação de variáveis de ambiente
├── pyproject.toml             # Dependências (uv)
├── .env.example               # Template de variáveis de ambiente
├── .env                       # Variáveis preenchidas — NÃO versionar
├── credentials.json           # Credenciais Gmail OAuth2 — NÃO versionar
├── token.json                 # Token OAuth2 (gerado automaticamente) — NÃO versionar
├── last_run.json              # Timestamp da última execução — NÃO versionar
├── agent.log                  # Log rotativo de execuções
├── graph/
│   ├── state.py               # EmailAgentState (TypedDict compartilhado)
│   ├── graph_builder.py       # Montagem do StateGraph e arestas condicionais
│   └── nodes/
│       ├── collect.py         # Nó 1 — Coleta Gmail
│       ├── chunk.py           # Nó 2 — Chunking
│       ├── analyze.py         # Nó 3 — Análise LLM
│       ├── validate.py        # Nó 4 — Validação de qualidade + retry
│       ├── filter_route.py    # Nó 5 — Filtro + Roteador
│       ├── alert.py           # Nó 6a — Alerta imediato (CRITICAL)
│       ├── format_digest.py   # Nó 6b — Formata digest
│       ├── summarize.py       # Nó 7 — Sumarização do dia
│       └── send.py            # Nó 8 — Envio (WhatsApp + fallback SMTP)
├── services/
│   ├── gmail_client.py        # Autenticação OAuth2 e coleta de e-mails
│   ├── evolution_client.py    # Envio de mensagens via Evolution API
│   └── smtp_client.py         # Envio de e-mail via SMTP (fallback)
├── skills/
│   └── email_analysis.md      # Prompt de análise do LLM
└── docs/
    └── requisitos_agente_email.md
```

---

## Logs

Todas as execuções são registradas em `agent.log` com rotação automática (5 MB por arquivo, 3 arquivos históricos):

```
2026-06-30 18:56:17 [INFO] graph.nodes.collect: Primeira execução — coletando últimas 24h
2026-06-30 18:56:18 [INFO] services.gmail_client: 52 mensagens encontradas
2026-06-30 18:58:50 [INFO] graph.nodes.validate: Nó 4: 52 válido(s), 0 para retry, 0 inválido(s)
2026-06-30 18:58:51 [INFO] graph.nodes.summarize: Nó 7: resumo gerado — 'Você tem 2 e-mails urgentes...'
2026-06-30 18:58:58 [INFO] graph.nodes.send: last_run.json atualizado
```

---

## Licença

Projeto educativo — uso livre.
