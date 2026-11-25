# Plano de Implementação: Sistema RAG Serverless (DynamoDB Vector + Python + React)

## 🎯 Objetivo
Desenvolver uma solução RAG (Retrieval-Augmented Generation) 100% serverless utilizando AWS DynamoDB, Amazon Bedrock (Titan Vector v2 + Claude 3), AWS Lambda (Python 3.12), API Gateway e React no Frontend.

---

## 🛠️ Stack Tecnológica & Arquitetura
- **IaC & Framework Backend:** AWS SAM (`template.yaml`), Python 3.12, `boto3`, `botocore`.
- **Database:** AWS DynamoDB (`blog-table` com Single Table Design e atributos de vetores).
- **IA / LLM:** 
  - Embeddings: `amazon.titan-embed-text-v2:0`
  - Geração de Texto: `anthropic.claude-3-sonnet-20240229-v1:0` (com retries/backoff para throttling).
- **Frontend:** React + Vite / CSS modernizado, comunicação com API Gateway HTTP API.
- **Scripts:** `seed.py` para geração de embeddings e inserção dos dados no DynamoDB.

---

## 📋 Fases e Tarefas de Implementação

### Fase 1: Planejamento & Estrutura de Diretórios
- [x] Criar arquivo de plano (`PLAN.md`)
- [ ] Criar estrutura de pastas do projeto (`backend/src`, `frontend/src`, etc.)

### Fase 2: Infraestrutura como Código (`backend/template.yaml`)
- [ ] Definir AWS SAM Template (`template.yaml`)
- [ ] Configurar Tabela DynamoDB (`blog-table`)
- [ ] Configurar Função Lambda (`ChatFunction`) em Python 3.12
- [ ] Configurar API Gateway (HTTP API `/chat` POST com CORS habilitado)
- [ ] Configurar Políticas de IAM com princípio do menor privilégio (`dynamodb:Scan`, `dynamodb:PutItem`, `bedrock:InvokeModel`)

### Fase 3: Script de Carga (`backend/seed.py`)
- [ ] Criar arquivo de dados com 3 posts sobre "O que é DynamoDB Vector" e "Python Serverless"
- [ ] Implementar chamada ao Bedrock Titan Embeddings v2
- [ ] Salvar registros e embeddings no DynamoDB (`blog-table`)

### Fase 4: Lógica do Backend RAG (`backend/src/chat_handler.py` & `requirements.txt`)
- [ ] Criar `requirements.txt` com dependências minimalistas
- [ ] Implementar Handler Lambda `/chat`
  - Parsing do payload HTTP POST
  - Geração de embedding da pergunta via Titan Text Embeddings V2
  - Busca por similaridade de cosseno nos vetores do DynamoDB (Top 3)
  - Construção do prompt enriquecido com contexto
  - Chamada ao Bedrock Claude 3 Sonnet / Haiku com tratamento robusto de throttling (`botocore.exceptions.ClientError` / `ThrottlingException`)
  - Resposta formatada JSON com cabeçalhos CORS

### Fase 5: Interface do Usuário (`frontend/`)
- [ ] Configurar `package.json`, Vite, React, CSS
- [ ] Criar interface de Chat responsiva e minimalista (`App.jsx` + `App.css`)
- [ ] Implementar integração via `fetch` para a API Serverless
- [ ] Tratamento de estados de carregamento (loading indicator), erro e exibição de fontes do contexto

### Fase 6: Documentação & Validação
- [ ] Criar `README.md` detalhado com instruções de deploy (`sam deploy --guided`), execução do `seed.py` e inicialização do frontend.

---

## ✅ Critérios de Aceite
1. SAM Template válido para deploy sem dependências externas pagas.
2. `seed.py` executa e popula o DynamoDB com vetores calculados pelo Titan Embeddings.
3. `chat_handler.py` realiza RAG completo ( embedding -> similaridade -> Bedrock -> resposta ) com retry em throttling.
4. Frontend React pronto para comunicação com a API e exibição amigável do histórico de chat.
