"""Testes do Exponential Backoff com Jitter."""

from unittest import mock

import pytest
from botocore.exceptions import ClientError


def _client_error(code):
    return ClientError({"Error": {"Code": code, "Message": "x"}}, "InvokeModel")


def test_backoff_retries_on_throttling_then_succeeds(ch, monkeypatch):
    monkeypatch.setattr(ch.time, "sleep", lambda *_: None)
    func = mock.Mock(side_effect=[_client_error("ThrottlingException"), "ok"])

    result = ch._invoke_with_backoff(func)

    assert result == "ok"
    assert func.call_count == 2


def test_backoff_gives_up_after_max_retries(ch, monkeypatch):
    monkeypatch.setattr(ch.time, "sleep", lambda *_: None)
    monkeypatch.setattr(ch, "MAX_RETRIES", 2)
    func = mock.Mock(side_effect=_client_error("TooManyRequestsException"))

    with pytest.raises(ClientError):
        ch._invoke_with_backoff(func)

    # tentativa inicial + 2 retries = 3 chamadas
    assert func.call_count == 3


def test_backoff_does_not_retry_non_throttling(ch):
    func = mock.Mock(side_effect=_client_error("ValidationException"))

    with pytest.raises(ClientError):
        ch._invoke_with_backoff(func)

    assert func.call_count == 1
