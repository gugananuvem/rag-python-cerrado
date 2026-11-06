"""Testes da busca vetorial via DynamoDB SearchVectors."""

import math


def _hit(item_id, title, content, score):
    """Monta um elemento de SearchResults no formato DynamoDB JSON."""
    return {
        "Item": {
            "id": {"S": item_id},
            "title": {"S": title},
            "content": {"S": content},
        },
        "Score": score,
    }


def test_search_vectors_called_with_index_and_top_k(ch):
    ch.dynamodb_client.search_vectors.return_value = {"SearchResults": []}

    ch.vector_search([0.5, -0.25], top_k=4)

    ch.dynamodb_client.search_vectors.assert_called_once_with(
        TableName=ch.TABLE_NAME,
        IndexName=ch.VECTOR_INDEX_NAME,
        SearchVector=[{"N": "0.5"}, {"N": "-0.25"}],
        TopK=4,
    )


def test_search_vector_is_plain_list_of_numbers_without_exponent(ch):
    result = ch._to_search_vector([1e-05, 1.5, -2e-10, 3])

    assert all(set(v) == {"N"} for v in result)
    assert result[0]["N"] == "0.00001"
    assert result[1]["N"] == "1.5"
    assert "e" not in result[2]["N"].lower()
    assert result[3]["N"] == "3"


def test_vector_search_deserializes_items_and_converts_distance_to_similarity(ch):
    ch.dynamodb_client.search_vectors.return_value = {
        "SearchResults": [
            _hit("a", "A", "ca", 0.0),
            _hit("c", "C", "cc", 0.25),
        ]
    }

    result = ch.vector_search([1.0, 0.0], top_k=2)

    assert [r["id"] for r in result] == ["a", "c"]
    assert result[0]["title"] == "A"
    assert result[0]["content"] == "ca"
    assert math.isclose(result[0]["score"], 1.0)
    assert math.isclose(result[1]["score"], 0.75)
    assert result[0]["score"] >= result[1]["score"]


def test_vector_search_keeps_order_returned_by_dynamodb(ch):
    ch.dynamodb_client.search_vectors.return_value = {
        "SearchResults": [_hit("x", "X", "cx", 0.1), _hit("y", "Y", "cy", 0.9)]
    }

    result = ch.vector_search([1.0], top_k=5)
    assert [r["id"] for r in result] == ["x", "y"]


def test_vector_search_returns_empty_list_when_no_results(ch):
    ch.dynamodb_client.search_vectors.return_value = {"SearchResults": []}
    assert ch.vector_search([1.0, 0.0]) == []


def test_vector_search_does_not_scan_the_table(ch):
    ch.dynamodb_client.search_vectors.return_value = {"SearchResults": []}

    ch.vector_search([1.0, 0.0])

    assert not ch.dynamodb_client.scan.called
    assert not ch.dynamodb_client.query.called
