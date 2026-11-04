# Sistema RAG Serverless (DynamoDB Vector + Python + React)

Sistema completo, de baixo custo e 100% Serverless para **Retrieval-Augmented Generation (RAG)** na AWS, usando **Amazon DynamoDB** (vector store), **Amazon Bedrock** (Titan Embeddings v2 + Claude 3 Sonnet), **AWS Lambda (Python 3.12)** e **React + Vite**.

---

## 📐 Arquitetura

```text
[ Usuário / Web ]
       │ (HTTP POST /chat)
       ▼
[ Frontend React (Vite / S3 + CloudFront) ]
       │
       ▼
[ API Gateway (HTTP API) ]
       │
       ▼
[ AWS Lambda (Python 3.12 - chat_handler.py) ]
       ├── 1. Embedding da pergunta ──► [ Bedrock: Titan Embeddings v2 ]
       ├── 2. Busca vetorial (cosseno) ──► [ DynamoDB: blog-table ]
       └── 3. Resposta com contexto ──► [ Bedrock: Claude 3 Sonnet ]
```

A busca vetorial é feita com um **scan no DynamoDB + cálculo de similaridade de cosseno em Python** sobre vetores de **1024 dimensões**. Essa abordagem mantém a arquitetura simples e barata para bases pequenas/médias.

---

## 📂 Estrutura

```text
demo-rag-serveless/
├── backend/
│   ├── src/
│   │   ├── chat_handler.py     # Lambda principal do RAG
│   │   └── requirements.txt    # boto3, botocore
│   ├── template.yaml           # IaC (AWS SAM)
│   └── seed.py                 # Popular a base com vetores
├── frontend/
│   ├── src/
│   │   ├── App.jsx             # Chat em React
│   │   ├── App.css
│   │   ├── main.jsx
│   │   └── index.css
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── PRD.md
├── PLAN.md
└── README.md
```

---

## 🛠️ Pré-requisitos

1. **AWS CLI** configurado (`aws configure`).
2. **AWS SAM CLI** instalado.
3. **Python 3.12**.
4. **Node.js 18+** e `npm`.
5. **Acesso aos modelos do Bedrock** (console → Bedrock → Model access):
   - `amazon.titan-embed-text-v2:0`
   - `anthropic.claude-3-sonnet-20240229-v1:0`

---

## 🚀 Deploy e Execução

### 1. Provisionar a infraestrutura (AWS SAM)

```bash
cd backend
sam build
sam deploy --guided
```

No `sam deploy --guided`, informe:
- **Stack Name**: `rag-dynamodb-stack`
- **AWS Region**: `us-east-1` (ou a região com Bedrock habilitado)
- Confirme as permissões de IAM.

Ao final, copie o output **`ApiEndpoint`**, algo como:

```text
https://abc123xyz.execute-api.us-east-1.amazonaws.com/chat
```

### 2. Popular a base de conhecimento

```bash
# ainda na pasta backend
pip install -r src/requirements.txt
python seed.py
```

O script gera embeddings dos posts de exemplo e grava na tabela `blog-table`.

> As credenciais/região usadas pelo `seed.py` vêm do seu ambiente AWS (variáveis `AWS_REGION`, perfil do AWS CLI, etc.).

### 3. Rodar o frontend React

```bash
cd ../frontend
npm install
npm run dev
```

Abra `http://localhost:3000`, clique na engrenagem ⚙️ e cole a URL do **ApiEndpoint**. A URL fica salva no `localStorage` do navegador.

---

## 🔌 Contrato da API

**Request** — `POST /chat`

```json
{ "question": "O que é RAG?" }
```

**Response** — `200 OK`

```json
{
  "answer": "RAG é uma técnica que...",
  "sources": [
    { "id": "post-001", "title": "O que é RAG...", "score": 0.82 }
  ]
}
```

---

## 🛡️ Destaques da implementação

- **Throttling resiliente**: `chat_handler.py` e `seed.py` usam **Exponential Backoff com Jitter** para `ThrottlingException` / `TooManyRequestsException`.
- **Busca vetorial em Python**: similaridade de cosseno sobre vetores de 1024 dimensões do Titan v2.
- **Transparência de fontes**: a resposta inclui as fontes mais relevantes e seus scores.
- **CORS flexível**: HTTP API e Lambda liberam requisições de CloudFront / localhost.
- **IAM mínimo**: a Lambda só tem leitura no DynamoDB e `InvokeModel` nos dois modelos específicos.

---

## ⚙️ Variáveis de ambiente (Lambda / seed)

| Variável                | Default                                      |
| ----------------------- | -------------------------------------------- |
| `AWS_REGION`            | `us-east-1`                                  |
| `TABLE_NAME`            | `blog-table`                                 |
| `EMBEDDING_MODEL_ID`    | `amazon.titan-embed-text-v2:0`               |
| `CHAT_MODEL_ID`         | `anthropic.claude-3-sonnet-20240229-v1:0`    |
| `EMBEDDING_DIMENSIONS`  | `1024`                                       |
| `TOP_K`                 | `3`                                          |

---

## 🧪 Testes

### Backend (pytest)

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest
```

17 testes cobrindo busca vetorial (cosseno + ranqueamento + paginação), o
`lambda_handler` (CORS, validação, happy path, base64) e o backoff com jitter.
Nenhum teste faz chamada real à AWS — os clientes do boto3 são mockados.

### Frontend (Vitest + Testing Library)

```bash
cd frontend
npm install
npm test          # execução única
npm run test:watch
```

6 testes cobrindo o painel de configuração, persistência do endpoint, envio de
pergunta com resposta/fontes, tratamento de erro e validação de entrada vazia.
O `fetch` é mockado.

---

## 💰 Custo & limitações

- **Custo**: DynamoDB on-demand + Lambda + Bedrock por uso. Para demos, tende a ficar em centavos de dólar.
- **Escala**: o `scan` + cosseno em Python é adequado para bases pequenas/médias. Para grandes volumes, migre para uma solução de vetores escalável (ex.: OpenSearch Serverless / Aurora pgvector).
