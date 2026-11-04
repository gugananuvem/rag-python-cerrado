"""
Lambda handler principal do sistema RAG Serverless.

Fluxo:
    1. Recebe a pergunta do usuário (POST /chat).
    2. Gera o embedding da pergunta via Amazon Bedrock (Titan Embeddings v2).
    3. Busca os documentos mais similares no DynamoDB (similaridade de cosseno em Python).
    4. Monta o contexto e gera a resposta final com Claude 3 Sonnet.
    5. Retorna a resposta + as fontes utilizadas (com score de similaridade).

Destaques:
    - Exponential Backoff com Jitter para lidar com ThrottlingException do Bedrock.
    - CORS liberado para o frontend React (CloudFront / localhost).
"""

import json
import math
import os
import random
import time
from decimal import Decimal
from typing import Any, Dict, List

import boto3
from botocore.exceptions import ClientError

# ----------------------------------------------------------------------------
# Configuração
# ----------------------------------------------------------------------------

REGION = os.environ.get("AWS_REGION", "us-east-1")
TABLE_NAME = os.environ.get("TABLE_NAME", "blog-table")
# Endpoint do DynamoDB. Deixe vazio para usar a AWS real; defina para o
# simulador local, ex.: http://localhost:8000
DYNAMODB_ENDPOINT = os.environ.get("DYNAMODB_ENDPOINT", "").strip() or None
# Profile nomeado do AWS CLI/credentials para uso local (ex.: dev).
# Deixe vazio em produção (Lambda usa a role via credenciais do ambiente).
AWS_PROFILE = os.environ.get("AWS_PROFILE", "").strip() or None
EMBEDDING_MODEL_ID = os.environ.get("EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")
CHAT_MODEL_ID = os.environ.get(
    "CHAT_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0"
)
EMBEDDING_DIMENSIONS = int(os.environ.get("EMBEDDING_DIMENSIONS", "1024"))
TOP_K = int(os.environ.get("TOP_K", "3"))

# Throttling / retry
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "6"))
BASE_DELAY = float(os.environ.get("BASE_DELAY", "1.0"))
MAX_DELAY = float(os.environ.get("MAX_DELAY", "20.0"))

THROTTLING_ERRORS = {
    "ThrottlingException",
    "TooManyRequestsException",
    "ProvisionedThroughputExceededException",
    "ServiceUnavailableException",
}

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "OPTIONS,POST",
}

# ----------------------------------------------------------------------------
# Clientes AWS (reutilizados entre invocações)
# ----------------------------------------------------------------------------

# Usa o profile nomeado quando definido (ambiente local); caso contrário,
# recai na cadeia de credenciais padrão (role do Lambda em produção).
session = boto3.Session(profile_name=AWS_PROFILE) if AWS_PROFILE else boto3.Session()

bedrock_runtime = session.client("bedrock-runtime", region_name=REGION)
dynamodb = session.resource("dynamodb", region_name=REGION, endpoint_url=DYNAMODB_ENDPOINT)
table = dynamodb.Table(TABLE_NAME)


# ----------------------------------------------------------------------------
# Retry com Exponential Backoff + Jitter
# ----------------------------------------------------------------------------


def _invoke_with_backoff(func, *args, **kwargs):
    """Executa `func` com retry em erros de throttling do Bedrock."""
    attempt = 0
    while True:
        try:
            return func(*args, **kwargs)
        except ClientError as err:
            code = err.response.get("Error", {}).get("Code", "")
            if code not in THROTTLING_ERRORS or attempt >= MAX_RETRIES:
                raise
            delay = min(MAX_DELAY, BASE_DELAY * (2 ** attempt))
            delay = delay * (0.5 + random.random())  # jitter
            print(
                f"[backoff] {code} - tentativa {attempt + 1}/{MAX_RETRIES}, "
                f"aguardando {delay:.2f}s"
            )
            time.sleep(delay)
            attempt += 1


# ----------------------------------------------------------------------------
# Bedrock: embeddings e chat
# ----------------------------------------------------------------------------


def get_embedding(text: str) -> List[float]:
    """Gera o embedding de um texto usando o Titan Embeddings v2."""
    body = json.dumps(
        {
            "inputText": text,
            "dimensions": EMBEDDING_DIMENSIONS,
            "normalize": True,
        }
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


def generate_answer(question: str, context_docs: List[Dict[str, Any]]) -> str:
    """Gera a resposta final com Claude 3 Sonnet usando o contexto recuperado."""
    context_text = "\n\n".join(
        f"[Fonte {i + 1}] {doc['title']}\n{doc['content']}"
        for i, doc in enumerate(context_docs)
    )

    system_prompt = (
        "Você é um assistente especializado que responde perguntas com base "
        "exclusivamente no CONTEXTO fornecido. Se a resposta não estiver no "
        "contexto, diga que não encontrou a informação. Responda em português, "
        "de forma clara e objetiva, citando as fontes quando relevante."
    )

    user_prompt = (
        f"CONTEXTO:\n{context_text}\n\n"
        f"PERGUNTA: {question}\n\n"
        "Responda usando apenas as informações do contexto acima."
    )

    body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "temperature": 0.2,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": user_prompt}]}
            ],
        }
    )

    def _call():
        return bedrock_runtime.invoke_model(
            modelId=CHAT_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=body,
        )

    response = _invoke_with_backoff(_call)
    payload = json.loads(response["body"].read())
    return payload["content"][0]["text"]


# ----------------------------------------------------------------------------
# Busca vetorial (similaridade de cosseno em Python)
# ----------------------------------------------------------------------------


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calcula a similaridade de cosseno entre dois vetores."""
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for x, y in zip(a, b):
        dot += x * y
        norm_a += x * x
        norm_b += y * y
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


def _to_float_list(raw: Any) -> List[float]:
    """Converte uma lista de Decimal (DynamoDB) para floats."""
    return [float(v) for v in raw]


def vector_search(query_embedding: List[float], top_k: int = TOP_K) -> List[Dict[str, Any]]:
    """
    Faz um scan na tabela do DynamoDB e ranqueia os documentos pela
    similaridade de cosseno em relação ao embedding da pergunta.
    """
    results: List[Dict[str, Any]] = []
    scan_kwargs: Dict[str, Any] = {}

    while True:
        response = table.scan(**scan_kwargs)
        for item in response.get("Items", []):
            embedding = item.get("embedding")
            if not embedding:
                continue
            score = cosine_similarity(query_embedding, _to_float_list(embedding))
            results.append(
                {
                    "id": item.get("id"),
                    "title": item.get("title", ""),
                    "content": item.get("content", ""),
                    "score": score,
                }
            )

        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_key

    results.sort(key=lambda d: d["score"], reverse=True)
    return results[:top_k]


# ----------------------------------------------------------------------------
# Handler
# ----------------------------------------------------------------------------


def _response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(body, ensure_ascii=False),
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    # Preflight CORS
    method = (
        event.get("requestContext", {}).get("http", {}).get("method")
        or event.get("httpMethod")
    )
    if method == "OPTIONS":
        return _response(200, {"message": "ok"})

    try:
        raw_body = event.get("body") or "{}"
        if event.get("isBase64Encoded"):
            import base64

            raw_body = base64.b64decode(raw_body).decode("utf-8")
        data = json.loads(raw_body)
        question = (data.get("question") or data.get("message") or "").strip()

        if not question:
            return _response(400, {"error": "Campo 'question' é obrigatório."})

        # 1. Embedding da pergunta
        query_embedding = get_embedding(question)

        # 2. Busca vetorial
        top_docs = vector_search(query_embedding, TOP_K)

        if not top_docs:
            return _response(
                200,
                {
                    "answer": "A base de conhecimento está vazia. Execute o seed.py primeiro.",
                    "sources": [],
                },
            )

        # 3. Geração da resposta
        answer = generate_answer(question, top_docs)

        sources = [
            {
                "id": doc["id"],
                "title": doc["title"],
                "score": round(doc["score"], 4),
            }
            for doc in top_docs
        ]

        return _response(200, {"answer": answer, "sources": sources})

    except ClientError as err:
        print(f"[erro] ClientError: {err}")
        return _response(502, {"error": "Falha ao chamar serviço AWS.", "detail": str(err)})
    except Exception as err:  # noqa: BLE001
        print(f"[erro] Inesperado: {err}")
        return _response(500, {"error": "Erro interno.", "detail": str(err)})
