# Sistema RAG Serverless (DynamoDB Vector + Python + React)

Um sistema completo, de baixo custo e 100% Serverless para **Retrieval-Augmented Generation (RAG)** na AWS, utilizando **Amazon DynamoDB Vector Search**, **Amazon Bedrock (Titan Embeddings v2 + Amazon Nova Micro)**, **AWS Lambda (Python 3.12)** e **React**.

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
       └── 3. Gera Resposta com Contexto ──► [ Amazon Bedrock (Amazon Nova Micro) ]
```

---

## 📂 Estrutura do Projeto

```text
/demo-rag-dynamodb
  ├── /backend
  │   ├── /src
  │   │   ├── chat_handler.py        # Função Lambda principal do RAG
  │   │   └── requirements.txt       # Dependências (boto3, botocore)
  │   ├── template.yaml              # Infraestrutura como Código (AWS SAM Template)
  │   ├── seed.py                    # Script para popular a base com vetores
  │   ├── package.json               # devDependency + scripts do simulador local
  │   ├── aws-local-simulator.json   # Config do AWS Local Simulator (DynamoDB local)
  │   └── server.js                  # Sobe o simulador local programaticamente
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
3. **Python 3.12** instalado **e disponível como `python` no PATH**.
   - O `sam build` valida o runtime pelo executável `python`/`python3` do PATH
     (não usa o launcher `py`). Se o `python` do PATH apontar para outra versão
     (ex.: 3.13/3.14), o build falha com
     `PythonPipBuilder:Validation - Binary validation failed for python ... runtime: python3.12`.
   - Instalar via winget: `winget install --id Python.Python.3.12 -e`
   - Garantir que `python --version` retorne `3.12.x`. Se houver outra versão na
     frente do PATH, mova a pasta do 3.12
     (`%LOCALAPPDATA%\Programs\Python\Python312` e `...\Python312\Scripts`) para o
     início do PATH do usuário, ou use build em container: `sam build --use-container`.
4. **Node.js 18+** e `npm` para executar o frontend e o AWS Local Simulator.
5. **Acesso aos modelos do Amazon Bedrock**:
   - `amazon.titan-embed-text-v2:0`
   - `us.amazon.nova-micro-v1:0`

> 💡 Para desenvolvimento local sem provisionar o DynamoDB na AWS, veja a seção
> [Ambiente de Desenvolvimento Local (AWS Local Simulator)](#-ambiente-de-desenvolvimento-local-aws-local-simulator).

---

## 🚀 Passo a Passo para Deploy e Execução

### 1. Provisionar a Infraestrutura na AWS (AWS SAM)

Navegue até a pasta `backend` e execute o deploy interativo do AWS SAM:

```bash
cd backend
sam build
sam deploy --guided
```

> ⚠️ **Python 3.12 obrigatório para o `sam build`.** O build valida o runtime
> `python3.12` pelo executável `python` do PATH. Confirme com `python --version`
> antes de rodar; se vier outra versão, ajuste o PATH (ver
> [Pré-requisitos](#️-pré-requisitos)) ou use `sam build --use-container`.

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

## 🧪 Ambiente de Desenvolvimento Local (AWS Local Simulator)

Para desenvolver e demonstrar sem provisionar recursos reais de armazenamento, o
projeto usa o **AWS Local Simulator** (`@gugananuvem/aws-local-simulator`), que
sobe um DynamoDB local (entre outros serviços) em `http://localhost:8000`.

> **Observação:** O simulador **não** emula o Amazon Bedrock. Os embeddings
> (Titan) e a geração de respostas (Nova Micro) continuam usando o **Bedrock real**.
> Apenas o DynamoDB roda localmente. Por isso é necessário um profile AWS válido
> com acesso ao Bedrock (ex.: `dev`).

### Arquivos envolvidos

```text
/backend
  ├── package.json                # devDependency + scripts do simulador
  ├── aws-local-simulator.json    # Config: serviços, portas e tabela blog-table
  └── server.js                   # Sobe o simulador via API programática
```

### 1. Instalar o simulador

Na pasta `backend`:

```bash
cd backend
npm install
```

Isso instala a devDependency `@gugananuvem/aws-local-simulator`.

### 2. Subir o simulador

Opção A — via `server.js` (recomendado, com shutdown gracioso):

```bash
npm start
```

Opção B — via CLI do simulador:

```bash
npm run simulator
```

O DynamoDB sobe em `http://localhost:8000` e a tabela **`blog-table`** é criada
automaticamente a partir do `aws-local-simulator.json`, já com o índice vetorial
`embedding-index` (atributo `embedding`, 1024 dimensões, COSINE) usado pelo
`SearchVectors`. Isso exige o simulador `>= 1.0.41`.

> **Tabela local criada antes do índice:** o simulador só aplica `VectorIndexes`
> do config na criação da tabela. Se `blog-table` já existe em
> `.aws-local-simulator-data`, adicione o índice sem perder os itens com
> `UpdateTable` (`VectorIndexUpdates` → `Create`, mesmo conteúdo do config) ou
> rode `npm run simulator:reset` e popule de novo com `python seed.py`.

#### Como o simulador executa a Lambda Python

O API Gateway local fica em `http://localhost:4567/chat` (`POST` e `OPTIONS`, como no
`template.yaml`) e aciona a lambda `rag-chat-handler`. Há dois modos:

| Modo | Comando | Config | Uso |
|------|---------|--------|-----|
| Padrão | `npm start` | `aws-local-simulator.json` (`codePath: "src"`) | O simulador cria um processo Python a cada requisição e carrega o `chat_handler`. Não precisa de mais nada rodando. Cada chamada paga o custo de iniciar Python e boto3. |
| Debug | `npm run start:debug` | `aws-local-simulator.debug.json` (`runtimeEndpoint`) | O simulador encaminha por HTTP para o `lambda_runtime_server.py` (porta 5001), que fica ativo. Suba-o pelo launch **Backend: Lambda (Python via simulador)** para parar em breakpoints. O `timeout` da lambda é 600 s para o breakpoint não estourar o tempo. |

No modo padrão o profile (`AWS_PROFILE=dev`), a região e o `DYNAMODB_ENDPOINT` vêm do
bloco `env` da lambda no `aws-local-simulator.json`. O processo usa o `python` do PATH
(3.12). Se `runtimeEndpoint` e `codePath` aparecerem juntos, o `runtimeEndpoint` vence.

Scripts auxiliares disponíveis:

```bash
npm run simulator:status   # status dos serviços
npm run simulator:reset    # zera os dados
npm run simulator:stop     # para o simulador
```

### 3. Configurar as variáveis de ambiente

Tanto `chat_handler.py` quanto `seed.py` leem variáveis de ambiente para alternar
entre o simulador local e a AWS real:

| Variável            | Uso                                                                 |
|---------------------|---------------------------------------------------------------------|
| `DYNAMODB_ENDPOINT` | Endpoint do DynamoDB. Vazio = AWS real; `http://localhost:8000` = local. |
| `AWS_PROFILE`       | Profile nomeado do AWS CLI (ex.: `dev`) para credenciais do Bedrock. Vazio em produção (usa a role do Lambda). |
| `AWS_REGION`        | Região (default `us-east-1`).                                       |

**PowerShell (Windows):**

```powershell
$env:AWS_PROFILE = "dev"
$env:DYNAMODB_ENDPOINT = "http://localhost:8000"
$env:AWS_REGION = "us-east-1"
```

**Bash (Linux/macOS):**

```bash
export AWS_PROFILE=dev
export DYNAMODB_ENDPOINT=http://localhost:8000
export AWS_REGION=us-east-1
```

### 4. Popular a base no DynamoDB local

Com o simulador rodando e as variáveis definidas:

```bash
pip install -r src/requirements.txt
python seed.py
```

Os embeddings são gerados no Bedrock real (profile `dev`) e os itens são gravados
no DynamoDB local.

### 5. Voltar para a AWS real

Basta remover a variável `DYNAMODB_ENDPOINT` (o `boto3` volta a usar o endpoint
real da AWS):

```powershell
Remove-Item Env:DYNAMODB_ENDPOINT   # PowerShell
```

```bash
unset DYNAMODB_ENDPOINT             # Bash
```

### Recriar a demonstração do zero (checklist)

1. Garantir **Python 3.12** no PATH (`python --version` → `3.12.x`). Necessário para o `sam build`.
2. `cd backend && npm install`
3. Confirmar que existem `aws-local-simulator.json`, `aws-local-simulator.debug.json` e `server.js` (incluídos no repo).
4. `npm start` para subir o simulador (DynamoDB em `:8000`, tabela `blog-table` criada, API em `:4567/chat`). Para debugar a Lambda, use `npm run start:debug` e o launch "Backend: Lambda (Python via simulador)".
5. Definir `AWS_PROFILE=dev`, `DYNAMODB_ENDPOINT=http://localhost:8000`, `AWS_REGION=us-east-1`.
6. `pip install -r src/requirements.txt && python seed.py` para popular a base.
7. (Opcional, deploy real) `sam build && sam deploy --guided`.
8. Rodar o frontend (`cd ../frontend && npm install && npm run dev`).

---

## 🛡️ Destaques da Implementação

- **Tratamento de Throttling do Bedrock**: Tanto o `chat_handler.py` quanto o `seed.py` possuem lógica resiliente de **Exponential Backoff com Jitter** para capturar exceções `ThrottlingException` e `TooManyRequestsException`.
- **Busca Vetorial Nativa no DynamoDB**: o `chat_handler.py` usa a API `SearchVectors` sobre o índice vetorial `embedding-index` (COSINE, 1024 dimensões do Titan Embeddings v2). O `Score` retornado é uma distância (0 = idêntico), convertida para similaridade (`1 - distância`) na resposta. Exige boto3/botocore `>= 1.43.119` e permissão `dynamodb:SearchVectors` no ARN do índice.
- **Transparência de Fontes**: A resposta da API inclui a lista das fontes mais relevantes do DynamoDB e seus respectivos scores de similaridade.
- **Configuração Flexível de CORS**: A HTTP API aceita requisições do frontend React via CloudFront ou localhost.
