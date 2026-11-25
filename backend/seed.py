#!/usr/bin/env python3
import json
import os
import time
import random
import boto3
from decimal import Decimal
from botocore.exceptions import ClientError

# Configuração de Tabela e Modelo Bedrock
TABLE_NAME = os.environ.get("TABLE_NAME", "blog-table")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
EMBEDDING_MODEL_ID = os.environ.get("BEDROCK_EMBEDDING_MODEL", "amazon.titan-embed-text-v2:0")

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
bedrock_runtime = boto3.client("bedrock-runtime", region_name=AWS_REGION)

# Base de Dados Fictícia de Exemplo (3 posts em conformidade com o PRD)
MOCK_POSTS = [
    {
        "id": "post-001",
        "sk": "POST#001",
        "metadata": {
            "title": "O que é DynamoDB Vector Search e Como Funciona",
            "category": "Database",
            "author": "Equipe Serverless",
            "date": "2026-03-15"
        },
        "content": (
            "O Amazon DynamoDB agora suporta busca vetorial (Vector Search), permitindo armazenar embeddings "
            "gerados por modelos de inteligência artificial diretamente em tabelas NoSQL. Com isso, é possível "
            "executar consultas de similaridade sem a necessidade de provisionar bancos vetoriais dedicados como "
            "Pinecone, OpenSearch ou Milvus. Os vetores são representados como listas numéricas e podem ser "
            "consultados para aplicações como RAG (Retrieval-Augmented Generation), busca semântica, recomendação de "
            "conteúdos e detecção de anomalias com baixíssima latência."
        )
    },
    {
        "id": "post-002",
        "sk": "POST#002",
        "metadata": {
            "title": "Aplicações RAG de Baixo Custo com Python Serverless na AWS",
            "category": "Architecture",
            "author": "Equipe Serverless",
            "date": "2026-03-20"
        },
        "content": (
            "Construir sistemas de RAG em arquitetura 100% Serverless utilizando Python 3.12, AWS Lambda, "
            "API Gateway e Amazon Bedrock reduz significativamente os custos operacionais. A execução sob demanda "
            "da AWS Lambda garante que você só pague pelo tempo exato em que as requisições estão sendo processadas. "
            "O modelo Amazon Titan Embeddings Text v2 gera vetores densos eficientes com dimensão de 1024, ideais para "
            "serem armazenados no DynamoDB. Quando combinado com modelos generativos como Anthropic Claude 3 Sonnet "
            "ou Haiku via Amazon Bedrock, você obtém uma solução de busca semântica de altíssima qualidade a fração "
            "de centavos por consulta."
        )
    },
    {
        "id": "post-003",
        "sk": "POST#003",
        "metadata": {
            "title": "Boas Práticas de Resiliência no Amazon Bedrock com Boto3 em Python",
            "category": "Backend",
            "author": "Equipe Serverless",
            "date": "2026-03-22"
        },
        "content": (
            "Ao integrar aplicações Python em AWS Lambda com o Amazon Bedrock utilizando a biblioteca Boto3, "
            "é fundamental tratar exceções de limite de taxa (throttling), como ThrottlingException e "
            "TooManyRequestsException. A estratégia recomendada é implementar retentativas exponenciais com tremor "
            "(Exponential Backoff with Jitter). Além disso, definir timeouts adequados no API Gateway e no Lambda, "
            "além de utilizar reutilização de conexões e variáveis de ambiente para IDs de modelos, torna a "
            "arquitetura serverless pronta para ambientes de produção com alta disponibilidade."
        )
    }
]

def generate_embedding_with_retry(text):
    """Chama o Amazon Bedrock Titan Text Embeddings v2 com retries para tratamento de Throttling."""
    body = json.dumps({
        "inputText": text,
        "dimensions": 1024,
        "normalize": True
    })
    
    max_retries = 5
    base_delay = 1.0
    
    for attempt in range(max_retries):
        try:
            response = bedrock_runtime.invoke_model(
                modelId=EMBEDDING_MODEL_ID,
                contentType="application/json",
                accept="application/json",
                body=body
            )
            response_body = json.loads(response["body"].read())
            return response_body.get("embedding", [])
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ["ThrottlingException", "TooManyRequestsException", "ProvisionedThroughputExceededException"]:
                if attempt == max_retries - 1:
                    print(f"❌ Limite de taxa excedido após {max_retries} tentativas: {e}")
                    raise e
                sleep_time = base_delay * (2 ** attempt) + random.uniform(0.1, 0.5)
                print(f"⚠️ Bedrock Throttling ({code}). Aguardando {sleep_time:.2f}s para tentar novamente ({attempt+1}/{max_retries})...")
                time.sleep(sleep_time)
            else:
                print(f"❌ Erro ao invocar Bedrock: {e}")
                raise e

def convert_floats_to_decimals(obj):
    """Converte números do tipo float em Decimal para compatibilidade com o Boto3 DynamoDB."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: convert_floats_to_decimals(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_floats_to_decimals(v) for v in obj]
    return obj

def seed_database():
    """Popula a tabela DynamoDB com os posts e seus respectivos embeddings."""
    print(f"🚀 Iniciando processo de carga (Seed) na tabela '{TABLE_NAME}' na região '{AWS_REGION}'...")
    table = dynamodb.Table(TABLE_NAME)
    
    for idx, post in enumerate(MOCK_POSTS, 1):
        print(f"\n[Post {idx}/{len(MOCK_POSTS)}] Gerando embedding para: '{post['metadata']['title']}'...")
        
        # Gerar o vetor de embedding com o conteúdo do post
        vector = generate_embedding_with_retry(post["content"])
        print(f"  ✅ Embedding gerado com sucesso! Tamanho do vetor: {len(vector)} dimensões.")
        
        # Preparar item para gravação no DynamoDB
        item = {
            "id": post["id"],
            "sk": post["sk"],
            "content": post["content"],
            "metadata": post["metadata"],
            "embedding": vector
        }
        
        # Converter floats para Decimal para Boto3
        item_decimal = convert_floats_to_decimals(item)
        
        print(f"  💾 Inserindo registro no DynamoDB...")
        table.put_item(Item=item_decimal)
        print(f"  🎉 Post '{post['id']}' gravado com sucesso!")
        
    print("\n✅ Carga inicial finalizada com sucesso! A base de conhecimento está pronta para o RAG.")

if __name__ == "__main__":
    seed_database()
