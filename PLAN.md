# PLAN.md — Plano de Desenvolvimento

Plano de implementação do sistema RAG Serverless (DynamoDB + Bedrock + Lambda + React).

## Fase 1 — Backend (RAG core)
- [x] `chat_handler.py`: handler Lambda com o pipeline de RAG
  - [x] Geração de embedding da pergunta (Titan Embeddings v2)
  - [x] Busca vetorial (scan no DynamoDB + similaridade de cosseno)
  - [x] Geração da resposta com contexto (Claude 3 Sonnet)
  - [x] Exponential Backoff com Jitter para throttling do Bedrock
  - [x] Resposta com fontes + scores + CORS
- [x] `requirements.txt` (boto3, botocore)

## Fase 2 — Infraestrutura (IaC)
- [x] `template.yaml` (AWS SAM)
  - [x] Tabela DynamoDB `blog-table` (PAY_PER_REQUEST)
  - [x] HTTP API com CORS
  - [x] Função Lambda Python 3.12 com variáveis de ambiente
  - [x] IAM: DynamoDB read + Bedrock InvokeModel (modelos específicos)
  - [x] Outputs: ApiEndpoint, TableName, FunctionName

## Fase 3 — Seed da base de conhecimento
- [x] `seed.py`
  - [x] Posts fictícios sobre RAG, DynamoDB, Bedrock, Serverless, etc.
  - [x] Geração de embeddings + gravação no DynamoDB (Decimal)
  - [x] Backoff com Jitter

## Fase 4 — Frontend (React + Vite)
- [x] Estrutura Vite (`index.html`, `vite.config.js`, `package.json`, `main.jsx`)
- [x] `App.jsx`: chat, configuração de endpoint (persistida em localStorage), fontes
- [x] `App.css` / `index.css`: estilos modernos (tema escuro)

## Fase 5 — Documentação
- [x] `README.md` com passo a passo de deploy e execução
- [x] `PLAN.md` (este arquivo)
- [x] `.gitignore`

## Fase 6 — Testes automatizados
- [x] Backend (pytest): busca vetorial, handler (CORS/validação/happy path/base64), backoff
- [x] Frontend (vitest + Testing Library): config, envio, fontes, erro, validação
- [x] Atualização do Vite 5 → 8 (elimina vulnerabilidades do esbuild no dev server)

## Próximos passos (fora do escopo atual)
- [x] Deploy real na AWS (`sam build` / `sam deploy --guided`)
- [ ] Autenticação na API (API Key / Cognito)
- [ ] Paginação / índice para bases grandes (migrar de scan para solução escalável)
