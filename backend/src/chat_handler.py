import json
import os
import math
import time
import random
import logging
import boto3
from botocore.exceptions import ClientError

# Configuração de Logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Inicialização dos clientes AWS
TABLE_NAME = os.environ.get("TABLE_NAME", "blog-table")
EMBEDDING_MODEL_ID = os.environ.get("BEDROCK_EMBEDDING_MODEL", "amazon.titan-embed-text-v2:0")
CLAUDE_MODEL_ID = os.environ.get("BEDROCK_CLAUDE_MODEL", "anthropic.claude-3-sonnet-20240229-v1:0")

dynamodb = boto3.resource("dynamodb")
bedrock_runtime = boto3.client("bedrock-runtime")

def calculate_cosine_similarity(vec_a, vec_b):
    """Calcula a similaridade de cosseno entre dois vetores de floats."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
        
    return dot_product / (norm_a * norm_b)

def invoke_bedrock_with_retry(model_id, body):
    """Executa a chamada ao Amazon Bedrock tratando throttling com Exponential Backoff."""
    max_retries = 5
    base_delay = 1.0
    
    for attempt in range(max_retries):
        try:
            response = bedrock_runtime.invoke_model(
                modelId=model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body)
            )
            return response
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ["ThrottlingException", "TooManyRequestsException", "ProvisionedThroughputExceededException"]:
                if attempt == max_retries - 1:
                    logger.error(f"Throttling no Bedrock após {max_retries} tentativas: {str(e)}")
                    raise e
                sleep_time = base_delay * (2 ** attempt) + random.uniform(0.1, 0.5)
                logger.warning(f"Bedrock Throttling ({error_code}). Tentativa {attempt + 1}/{max_retries}. Aguardando {sleep_time:.2f}s...")
                time.sleep(sleep_time)
            else:
                logger.error(f"Erro ao chamar modelo Bedrock {model_id}: {str(e)}")
                raise e

def get_question_embedding(text):
    """Gera o vetor de embedding para o texto utilizando Amazon Titan Embeddings v2."""
    body = {
        "inputText": text,
        "dimensions": 1024,
        "normalize": True
    }
    
    response = invoke_bedrock_with_retry(EMBEDDING_MODEL_ID, body)
    response_body = json.loads(response["body"].read())
    return response_body.get("embedding", [])

def search_top_k_posts(query_vector, top_k=3):
    """Busca no DynamoDB os posts com maior similaridade de vetor."""
    table = dynamodb.Table(TABLE_NAME)
    
    # Realiza scan para recuperar os registros que possuem embeddings gravados
    response = table.scan(
        FilterExpression="attribute_exists(embedding)"
    )
    items = response.get("Items", [])
    
    # Paginação do DynamoDB caso haja mais itens
    while "LastEvaluatedKey" in response:
        response = table.scan(
            FilterExpression="attribute_exists(embedding)",
            ExclusiveStartKey=response["LastEvaluatedKey"]
        )
        items.extend(response.get("Items", []))
    
    scored_posts = []
    for item in items:
        raw_embedding = item.get("embedding", [])
        # Converte itens Decimal do DynamoDB para float
        embedding = [float(val) for val in raw_embedding]
        
        similarity = calculate_cosine_similarity(query_vector, embedding)
        scored_posts.append({
            "id": item.get("id"),
            "sk": item.get("sk"),
            "content": item.get("content", ""),
            "metadata": item.get("metadata", {}),
            "similarity": similarity
        })
    
    # Ordena de forma decrescente pelo score de similaridade e pega os K primeiros
    scored_posts.sort(key=lambda x: x["similarity"], reverse=True)
    return scored_posts[:top_k]

def generate_rag_response(question, retrieved_posts):
    """Gera a resposta final utilizando Claude 3 via Bedrock com base no contexto recuperado."""
    context_str = "\n\n---\n\n".join([
        f"Fonte (ID: {p['id']} - {p.get('metadata', {}).get('title', 'Post')}):\n{p['content']}"
        for p in retrieved_posts
    ])
    
    system_prompt = (
        "Você é um assistente virtual especialista em AWS, DynamoDB e Arquiteturas Serverless.\n"
        "Responda à pergunta do usuário utilizando primariamente o contexto fornecido abaixo.\n"
        "Se a informação não estiver presente no contexto, responda com o seu conhecimento prévio, "
        "mas indique que essa informação adicional não estava nos documentos da base de conhecimento.\n"
        "Seja direto, claro, técnico e utilize formatação em Markdown amigável."
    )
    
    user_prompt = f"Contexto Recuperado:\n{context_str}\n\nPergunta do Usuário:\n{question}"
    
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "temperature": 0.3,
        "system": system_prompt,
        "messages": [
            {
                "role": "user",
                "content": user_prompt
            }
        ]
    }
    
    response = invoke_bedrock_with_retry(CLAUDE_MODEL_ID, body)
    response_body = json.loads(response["body"].read())
    
    # Extrai o texto da resposta do Claude 3
    content_blocks = response_body.get("content", [])
    answer = "".join([block.get("text", "") for block in content_blocks if block.get("type") == "text"])
    
    return answer

def lambda_handler(event, context):
    """Handler Principal da Função AWS Lambda."""
    cors_headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "POST,OPTIONS"
    }
    
    # Trata requisições Preflight do CORS (OPTIONS)
    http_method = event.get("requestContext", {}).get("http", {}).get("method") or event.get("httpMethod")
    if http_method == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": cors_headers,
            "body": json.dumps({"message": "CORS OK"})
        }
    
    try:
        body = event.get("body")
        if isinstance(body, str):
            body = json.loads(body)
        elif not body:
            body = {}
            
        pergunta = body.get("pergunta") or body.get("question")
        
        if not pergunta or not pergunta.strip():
            return {
                "statusCode": 400,
                "headers": cors_headers,
                "body": json.dumps({"error": "Campo 'pergunta' é obrigatório no JSON."})
            }
            
        logger.info(f"Processando pergunta: {pergunta}")
        
        # 1. Gerar embedding da pergunta do usuário
        query_vector = get_question_embedding(pergunta)
        
        # 2. Buscar posts no DynamoDB ordenados por similaridade
        top_posts = search_top_k_posts(query_vector, top_k=3)
        logger.info(f"Recuperados {len(top_posts)} posts mais similares.")
        
        # 3. Gerar resposta enriquecida com Claude 3
        resposta = generate_rag_response(pergunta, top_posts)
        
        # Formatar fontes de contexto simplificadas para retornar ao cliente
        fontes = [
            {
                "id": p["id"],
                "title": p.get("metadata", {}).get("title", f"Post {p['id']}"),
                "similarity": round(p["similarity"], 4),
                "snippet": p["content"][:150] + "..." if len(p["content"]) > 150 else p["content"]
            }
            for p in top_posts
        ]
        
        return {
            "statusCode": 200,
            "headers": cors_headers,
            "body": json.dumps({
                "resposta": resposta,
                "fontes": fontes
            }, ensure_ascii=False)
        }
        
    except ClientError as ce:
        logger.error(f"Erro de AWS ClientError: {str(ce)}", exc_info=True)
        return {
            "statusCode": 500,
            "headers": cors_headers,
            "body": json.dumps({"error": "Erro no processamento AWS.", "details": str(ce)})
        }
    except Exception as e:
        logger.error(f"Erro interno no Lambda: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "headers": cors_headers,
            "body": json.dumps({"error": "Erro interno do servidor.", "details": str(e)})
        }
