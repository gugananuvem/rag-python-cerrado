"""Testes da lógica de busca vetorial (cosseno + ranqueamento)."""

import math
from decimal import Decimal


def test_cosine_identical_vectors(ch):
    assert math.isclose(ch.cosine_similarity([1, 0, 0], [1, 0, 0]), 1.0, abs_tol=1e-9)


def test_cosine_orthogonal_vectors(ch):
    assert math.isclose(ch.cosine_similarity([1, 0], [0, 1]), 0.0, abs_tol=1e-9)


def test_cosine_opposite_vectors(ch):
    assert math.isclose(ch.cosine_similarity([1, 0], [-1, 0]), -1.0, abs_tol=1e-9)


def test_cosine_zero_vector_returns_zero(ch):
    assert ch.cosine_similarity([0, 0], [1, 1]) == 0.0


def test_vector_search_ranks_by_similarity(ch):
    items = [
        {"id": "a", "title": "A", "content": "ca", "embedding": [Decimal("1"), Decimal("0")]},
        {"id": "b", "title": "B", "content": "cb", "embedding": [Decimal("0"), Decimal("1")]},
        {"id": "c", "title": "C", "content": "cc", "embedding": [Decimal("0.9"), Decimal("0.1")]},
    ]
    ch.table.scan.return_value = {"Items": items}

    result = ch.vector_search([1.0, 0.0], top_k=2)

    assert [r["id"] for r in result] == ["a", "c"]
    assert result[0]["score"] >= result[1]["score"]


def test_vector_search_respects_top_k(ch):
    items = [
        {"id": str(i), "title": "t", "content": "c", "embedding": [Decimal("1"), Decimal(str(i))]}
        for i in range(5)
    ]
    ch.table.scan.return_value = {"Items": items}

    result = ch.vector_search([1.0, 0.0], top_k=3)
    assert len(result) == 3


def test_vector_search_skips_items_without_embedding(ch):
    items = [
        {"id": "a", "title": "A", "content": "ca", "embedding": [Decimal("1"), Decimal("0")]},
        {"id": "no-emb", "title": "X", "content": "cx"},
    ]
    ch.table.scan.return_value = {"Items": items}

    result = ch.vector_search([1.0, 0.0], top_k=5)
    assert [r["id"] for r in result] == ["a"]


def test_vector_search_paginates(ch):
    page1 = {
        "Items": [{"id": "a", "title": "A", "content": "ca", "embedding": [Decimal("1"), Decimal("0")]}],
        "LastEvaluatedKey": {"id": "a"},
    }
    page2 = {
        "Items": [{"id": "b", "title": "B", "content": "cb", "embedding": [Decimal("0.5"), Decimal("0.5")]}],
    }
    ch.table.scan.side_effect = [page1, page2]

    result = ch.vector_search([1.0, 0.0], top_k=5)
    ids = {r["id"] for r in result}
    assert ids == {"a", "b"}
    assert ch.table.scan.call_count == 2
