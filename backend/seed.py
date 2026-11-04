"""
Script para popular a base de conhecimento (DynamoDB) com posts fictícios.

Para cada post:
    1. Gera o embedding do conteúdo via Amazon Bedrock (Titan Embeddings v2).
    2. Grava o item (id, title, content, embedding) na tabela DynamoDB.

Uso:
    pip install -r src/requirements.txt
    python seed.py

Variáveis de ambiente opcionais:
    AWS_REGION            (default: us-east-1)
    TABLE_NAME            (default: blog-table)
    EMBEDDING_MODEL_ID    (default: amazon.titan-embed-text-v2:0)
    EMBEDDING_DIMENSIONS  (default: 1024)
"""

import json
import os
import random
import time
from decimal import Decimal
from typing import List

import boto3
from botocore.exceptions import ClientError

REGION = os.environ.get("AWS_REGION", "us-east-1")
TABLE_NAME = os.environ.get("TABLE_NAME", "blog-table")
# Endpoint do DynamoDB. Deixe vazio para usar a AWS real; defina para o
# simulador local, ex.: http://localhost:8000
DYNAMODB_ENDPOINT = os.environ.get("DYNAMODB_ENDPOINT", "").strip() or None
# Profile nomeado do AWS CLI/credentials para uso local (ex.: dev).
AWS_PROFILE = os.environ.get("AWS_PROFILE", "").strip() or None
EMBEDDING_MODEL_ID = os.environ.get("EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")
EMBEDDING_DIMENSIONS = int(os.environ.get("EMBEDDING_DIMENSIONS", "1024"))

MAX_RETRIES = 6
BASE_DELAY = 1.0
MAX_DELAY = 20.0
THROTTLING_ERRORS = {
    "ThrottlingException",
    "TooManyRequestsException",
    "ServiceUnavailableException",
}

# Usa o profile nomeado quando definido (ambiente local); caso contrário,
# recai na cadeia de credenciais padrão.
session = boto3.Session(profile_name=AWS_PROFILE) if AWS_PROFILE else boto3.Session()

bedrock_runtime = session.client("bedrock-runtime", region_name=REGION)
dynamodb = session.resource("dynamodb", region_name=REGION, endpoint_url=DYNAMODB_ENDPOINT)
table = dynamodb.Table(TABLE_NAME)


# ----------------------------------------------------------------------------
# Posts fictícios (base de conhecimento de exemplo)
# ----------------------------------------------------------------------------

POSTS = [
    {
        "id": "post-001",
        "title": "O que é RAG (Retrieval-Augmented Generation)",
        "content": (
            "RAG é uma técnica que combina recuperação de informações com geração "
            "de texto por LLMs. Em vez de depender apenas do conhecimento interno do "
            "modelo, o sistema busca documentos relevantes em uma base de dados e os "
            "injeta como contexto no prompt. Isso reduz alucinações, permite respostas "
            "atualizadas e torna possível citar as fontes utilizadas."
        ),
    },
    {
        "id": "post-002",
        "title": "Amazon DynamoDB como Vector Store",
        "content": (
            "O Amazon DynamoDB é um banco NoSQL serverless totalmente gerenciado. É "
            "possível usá-lo como armazenamento de vetores guardando os embeddings como "
            "listas numéricas em cada item. Para bases pequenas, a busca por similaridade "
            "pode ser feita com um scan e cálculo de cosseno na aplicação, mantendo a "
            "arquitetura 100% serverless e de baixo custo."
        ),
    },
    {
        "id": "post-003",
        "title": "Amazon Bedrock e os modelos Titan e Claude",
        "content": (
            "O Amazon Bedrock oferece acesso a modelos de fundação via API. O Titan "
            "Embeddings v2 converte textos em vetores de 1024 dimensões, ideais para "
            "busca semântica. Já o Claude 3 Sonnet, da Anthropic, é um modelo de "
            "linguagem usado para gerar respostas naturais a partir do contexto "
            "recuperado em um pipeline de RAG."
        ),
    },
    {
        "id": "post-004",
        "title": "Arquitetura Serverless na AWS",
        "content": (
            "Uma arquitetura serverless elimina a necessidade de gerenciar servidores. "
            "Na AWS, o AWS Lambda executa o código sob demanda, o API Gateway expõe "
            "endpoints HTTP, o DynamoDB armazena dados e o S3 com CloudFront serve o "
            "frontend. Você paga apenas pelo uso, o que torna a solução econômica para "
            "cargas variáveis."
        ),
    },
    {
        "id": "post-005",
        "title": "Tratamento de Throttling no Amazon Bedrock",
        "content": (
            "APIs do Bedrock podem retornar ThrottlingException ou TooManyRequestsException "
            "sob alta demanda. A estratégia recomendada é o Exponential Backoff com Jitter: "
            "a cada nova tentativa, o tempo de espera cresce exponencialmente e recebe um "
            "componente aleatório para evitar que várias chamadas sejam reenviadas no mesmo "
            "instante, aumentando a resiliência da aplicação."
        ),
    },
    {
        "id": "post-006",
        "title": "Similaridade de Cosseno na Busca Semântica",
        "content": (
            "A similaridade de cosseno mede o ângulo entre dois vetores, retornando um "
            "valor entre -1 e 1. Em busca semântica, quanto mais próximo de 1, mais "
            "parecidos são os significados dos textos representados pelos embeddings. É a "
            "métrica mais usada para ranquear documentos em sistemas de RAG."
        ),
    },
    {
        "id": "post-007",
        "title": "React com Vite para Frontends Modernos",
        "content": (
            "O Vite é uma ferramenta de build moderna que oferece servidor de "
            "desenvolvimento ultrarrápido e hot module replacement. Combinado com React, "
            "permite criar interfaces reativas com configuração mínima. É ideal para "
            "aplicações de chat que consomem APIs serverless, como o frontend deste "
            "sistema de RAG."
        ),
    },
    {
        "id": "post-008",
        "title": "Boas práticas de CORS em HTTP APIs",
        "content": (
            "CORS (Cross-Origin Resource Sharing) controla quais origens podem consumir "
            "uma API pelo navegador. Em uma HTTP API do API Gateway, configura-se as "
            "origens, métodos e cabeçalhos permitidos. Para um frontend React servido via "
            "CloudFront ou localhost, é preciso liberar os métodos POST e OPTIONS e o "
            "cabeçalho Content-Type."
        ),
    },
]


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------


def _invoke_with_backoff(func, *args, **kwargs):
    attempt = 0
    while True:
        try:
            return func(*args, **kwargs)
        except ClientError as err:
            code = err.response.get("Error", {}).get("Code", "")
            if code not in THROTTLING_ERRORS or attempt >= MAX_RETRIES:
                raise
            delay = min(MAX_DELAY, BASE_DELAY * (2 ** attempt)) * (0.5 + random.random())
            print(f"  [backoff] {code} - aguardando {delay:.2f}s")
            time.sleep(delay)
            attempt += 1


def get_embedding(text: str) -> List[float]:
    body = json.dumps(
        {"inputText": text, "dimensions": EMBEDDING_DIMENSIONS, "normalize": True}
    )

    def _call():
        return bedrock_runtime.invoke_model(
            modelId=EMBEDDING_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=body,
        )

    response = _invoke_with_backoff(_call)
    payload = json.loads(response["body"].read())
    return payload["embedding"]


def to_dynamo_number_list(vector: List[float]) -> List[Decimal]:
    """DynamoDB não aceita float; converte para Decimal."""
    return [Decimal(str(v)) for v in vector]


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------


def main() -> None:
    print(f"Populando a tabela '{TABLE_NAME}' na região '{REGION}'...\n")
    for post in POSTS:
        text = f"{post['title']}. {post['content']}"
        print(f"- Gerando embedding: {post['id']} ({post['title']})")
        embedding = get_embedding(text)
        table.put_item(
            Item={
                "id": post["id"],
                "title": post["title"],
                "content": post["content"],
                "embedding": to_dynamo_number_list(embedding),
            }
        )
        print(f"  gravado ({len(embedding)} dimensões).")

    print(f"\nConcluído. {len(POSTS)} posts inseridos em '{TABLE_NAME}'.")


if __name__ == "__main__":
    main()
