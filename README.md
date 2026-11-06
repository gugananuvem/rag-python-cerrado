# Sistema RAG Serverless (DynamoDB Vector + Python + React)

Sistema completo, de baixo custo e 100% Serverless para **Retrieval-Augmented Generation (RAG)** na AWS, usando **Amazon DynamoDB** (vector store), **Amazon Bedrock** (Titan Embeddings v2 + Amazon Nova Micro), **AWS Lambda (Python 3.12)** e **React + Vite**.

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
       ├── 2. Busca vetorial (SearchVectors) ──► [ DynamoDB: blog-table ]
       └── 3. Resposta com contexto ──► [ Bedrock: Amazon Nova Micro ]
```

A busca vetorial usa o **índice vetorial nativo do DynamoDB** (API `SearchVectors`) sobre vetores de **1024 dimensões**, com distância **COSINE**. Não há scan nem cálculo de similaridade no Python: o DynamoDB devolve os `TopK` itens mais próximos. O índice (`embedding-index`, atributo `embedding`) é declarado no `template.yaml` e exige a tabela em modo on-demand.

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
   - `us.amazon.nova-micro-v1:0`

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
- **Busca vetorial nativa**: `SearchVectors` no índice vetorial do DynamoDB (COSINE, 1024 dimensões do Titan v2).
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
| `CHAT_MODEL_ID`         | `us.amazon.nova-micro-v1:0`    |
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

15 testes cobrindo busca vetorial (`SearchVectors`: formato do `SearchVector`, conversão de score e ordenação), o
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
- **Escala**: a busca usa o índice vetorial do DynamoDB (`SearchVectors`, aproximada), sem varrer a tabela. Cada tabela aceita até 5 índices vetoriais e eles só funcionam com a tabela em modo on-demand.
