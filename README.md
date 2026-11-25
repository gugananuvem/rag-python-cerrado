# Sistema RAG Serverless (DynamoDB Vector + Python + React)

Um sistema completo, de baixo custo e 100% Serverless para **Retrieval-Augmented Generation (RAG)** na AWS, utilizando **Amazon DynamoDB Vector Search**, **Amazon Bedrock (Titan Embeddings v2 + Claude 3)**, **AWS Lambda (Python 3.12)** e **React**.

---

## 📐 Arquitetura da Solução

```text
[ Usuário / Web ]
       │
       ▼
[ Frontend React (S3 + CloudFront / Vite Local) ]
       │
       ▼ (HTTP POST /chat)
[ API Gateway (HTTP API) ]
       │
       ▼
[ AWS Lambda (Python 3.12 - chat_handler.py) ]
       ├── 1. Gera Embedding da Pergunta ──► [ Amazon Bedrock (Titan Vector v2) ]
       ├── 2. Consulta Similaridade Vetorial ──► [ Amazon DynamoDB (blog-table) ]
       └── 3. Gera Resposta com Contexto ──► [ Amazon Bedrock (Claude 3 Sonnet) ]
```

---

## 📂 Estrutura do Projeto

```text
/demo-rag-dynamodb
  ├── /backend
  │   ├── /src
  │   │   ├── chat_handler.py    # Função Lambda principal do RAG
  │   │   └── requirements.txt   # Dependências (boto3, botocore)
  │   ├── template.yaml          # Infraestrutura como Código (AWS SAM Template)
  │   └── seed.py                # Script para popular a base com vetores
  ├── /frontend
  │   ├── /src
  │   │   ├── App.jsx            # Componente de Chat em React
  │   │   ├── App.css            # Estilos modernos
  │   │   ├── main.jsx           # Entrypoint do React
  │   │   └── index.css          # Estilos globais
  │   ├── index.html
  │   ├── package.json
  │   └── vite.config.js
  ├── PLAN.md                    # Plano de Desenvolvimento do Projeto
  └── README.md                  # Documentação do Projeto
```

---

## 🛠️ Pré-requisitos

1. **AWS CLI** configurado (`aws configure`) com credenciais válidas.
2. **AWS SAM CLI** instalado.
3. **Python 3.12** instalado.
4. **Node.js 18+** e `npm` para executar o frontend.
5. **Acesso aos modelos do Amazon Bedrock**:
   - `amazon.titan-embed-text-v2:0`
   - `anthropic.claude-3-sonnet-20240229-v1:0`

---

## 🚀 Passo a Passo para Deploy e Execução

### 1. Provisionar a Infraestrutura na AWS (AWS SAM)

Navegue até a pasta `backend` e execute o deploy interativo do AWS SAM:

```bash
cd backend
sam build
sam deploy --guided
```

Durante o `sam deploy --guided`, informe:
- **Stack Name**: `rag-dynamodb-stack`
- **AWS Region**: `us-east-1` (ou a região configurada no Bedrock)
- Confirme as autorizações de IAM e permissões Padrão.

No final da execução, o SAM exibirá o Output **`ApiEndpoint`**, exemplo:
```text
https://abc123xyz.execute-api.us-east-1.amazonaws.com/chat
```

---

### 2. Popular a Base de Conhecimento (DynamoDB Vector Seed)

Ainda na pasta `backend`, instale as dependências e execute o script `seed.py` para gerar os vetores dos posts fictícios no Bedrock e gravá-los no DynamoDB:

```bash
pip install -r src/requirements.txt
python seed.py
```

*Nota: O script utilizará a tabela `blog-table` criada na AWS.*

---

### 3. Rodar o Frontend React Localmente

Navegue até a pasta `frontend` e inicie a aplicação:

```bash
cd ../frontend
npm install
npm run dev
```

Abra o navegador em `http://localhost:3000`.

Clique no ícone de engrenagem ⚙️ no canto superior direito e cole a URL do **ApiEndpoint** gerada no Passo 1.

---

## 🛡️ Destaques da Implementação

- **Tratamento de Throttling do Bedrock**: Tanto o `chat_handler.py` quanto o `seed.py` possuem lógica resiliente de **Exponential Backoff com Jitter** para capturar exceções `ThrottlingException` e `TooManyRequestsException`.
- **Busca Vetorial Nativa em Python/DynamoDB**: Cálculo de similaridade de cosseno direto sobre os vetores de 1024 dimensões do Titan Embeddings v2.
- **Transparência de Fontes**: A resposta da API inclui a lista das fontes mais relevantes do DynamoDB e seus respectivos scores de similaridade.
- **Configuração Flexível de CORS**: A HTTP API aceita requisições do frontend React via CloudFront ou localhost.
