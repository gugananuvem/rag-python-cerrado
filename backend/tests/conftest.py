"""
Configuração compartilhada dos testes.

Importa o módulo `chat_handler` com os clientes AWS mockados, de modo que
nenhum teste faça chamadas reais à AWS. Expõe o módulo via a fixture `ch`.
"""

import os
import sys
from unittest import mock

import pytest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BACKEND_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)


@pytest.fixture()
def ch():
    """Importa chat_handler com boto3 mockado e reseta a tabela por teste."""
    import boto3

    with mock.patch.object(boto3, "client"), mock.patch.object(
        boto3, "resource"
    ), mock.patch.object(boto3, "Session"):
        # Garante import limpo caso outro teste já tenha importado
        sys.modules.pop("chat_handler", None)
        import chat_handler as module

    module.bedrock_runtime = mock.Mock()
    module.table = mock.Mock()
    return module
