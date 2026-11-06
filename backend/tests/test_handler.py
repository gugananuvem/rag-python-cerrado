"""Testes do lambda_handler (fluxo HTTP + CORS + validação)."""

import json
from unittest import mock


def _hit(item_id, title, content, score):
    """Elemento de SearchResults do DynamoDB SearchVectors (DynamoDB JSON)."""
    return {
        "Item": {"id": {"S": item_id}, "title": {"S": title}, "content": {"S": content}},
        "Score": score,
    }


def _post(body, is_b64=False):
    return {
        "requestContext": {"http": {"method": "POST"}},
        "body": body,
        "isBase64Encoded": is_b64,
    }


def test_options_preflight_returns_cors(ch):
    event = {"requestContext": {"http": {"method": "OPTIONS"}}}
    resp = ch.lambda_handler(event, None)

    assert resp["statusCode"] == 200
    assert resp["headers"]["Access-Control-Allow-Origin"] == "*"


def test_missing_question_returns_400(ch):
    resp = ch.lambda_handler(_post(json.dumps({})), None)
    assert resp["statusCode"] == 400
    assert "error" in json.loads(resp["body"])


def test_empty_knowledge_base_returns_message(ch):
    ch.get_embedding = mock.Mock(return_value=[0.1, 0.2])
    ch.dynamodb_client.search_vectors.return_value = {"SearchResults": []}

    resp = ch.lambda_handler(_post(json.dumps({"question": "oi?"})), None)
    body = json.loads(resp["body"])

    assert resp["statusCode"] == 200
    assert body["sources"] == []


def test_happy_path_returns_answer_and_sources(ch, monkeypatch):
    monkeypatch.setattr(ch, "get_embedding", lambda _t: [1.0, 0.0])
    monkeypatch.setattr(ch, "generate_answer", lambda _q, _docs: "resposta final")

    ch.dynamodb_client.search_vectors.return_value = {
        "SearchResults": [
            _hit("p1", "T1", "c1", 0.0),
            _hit("p2", "T2", "c2", 1.0),
        ]
    }

    resp = ch.lambda_handler(_post(json.dumps({"question": "o que e rag?"})), None)
    body = json.loads(resp["body"])

    assert resp["statusCode"] == 200
    assert body["answer"] == "resposta final"
    assert body["sources"][0]["id"] == "p1"
    assert "score" in body["sources"][0]


def test_accepts_message_field_alias(ch, monkeypatch):
    monkeypatch.setattr(ch, "get_embedding", lambda _t: [1.0, 0.0])
    monkeypatch.setattr(ch, "generate_answer", lambda _q, _docs: "ok")

    ch.dynamodb_client.search_vectors.return_value = {"SearchResults": [_hit("p1", "T1", "c1", 0.0)]}

    resp = ch.lambda_handler(_post(json.dumps({"message": "usando alias"})), None)
    assert resp["statusCode"] == 200


def test_base64_encoded_body(ch, monkeypatch):
    import base64

    monkeypatch.setattr(ch, "get_embedding", lambda _t: [1.0])
    monkeypatch.setattr(ch, "generate_answer", lambda _q, _docs: "ok")

    ch.dynamodb_client.search_vectors.return_value = {"SearchResults": [_hit("p1", "T1", "c1", 0.0)]}

    raw = base64.b64encode(json.dumps({"question": "x"}).encode()).decode()
    resp = ch.lambda_handler(_post(raw, is_b64=True), None)
    assert resp["statusCode"] == 200
