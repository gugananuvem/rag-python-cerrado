"""
Runtime server genérico para o AWS Local Simulator (ponte HTTP poliglota).

O simulador, ao invocar uma Lambda com runtime externo (ex.: python3.12),
faz um POST para este servidor com o corpo:

    { "event": <evento Lambda>, "context": <context serializável> }

Este servidor importa o handler indicado pela variável de ambiente
LAMBDA_HANDLER (formato "modulo.funcao", padrão "chat_handler.lambda_handler"),
chama handler(event, context) e devolve o resultado como JSON.

Mantém o processo Python vivo, o que permite:
  - anexar o debugpy e parar em breakpoints no handler;
  - reusar os clientes boto3 entre invocações (como numa Lambda quente).

Variáveis de ambiente:
    LAMBDA_HANDLER   (default: chat_handler.lambda_handler)
    LAMBDA_TASK_ROOT (default: src)  -> pasta adicionada ao sys.path
    RUNTIME_HOST     (default: 127.0.0.1)
    RUNTIME_PORT     (default: 5001)
    RUNTIME_PATH     (default: /invoke)

Uso:
    python lambda_runtime_server.py
"""

import importlib
import io
import json
import os
import sys
import traceback
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# ----------------------------------------------------------------------------
# Configuração
# ----------------------------------------------------------------------------

HANDLER_SPEC = os.environ.get("LAMBDA_HANDLER", "chat_handler.lambda_handler")
TASK_ROOT = os.environ.get("LAMBDA_TASK_ROOT", "src")
HOST = os.environ.get("RUNTIME_HOST", "127.0.0.1")
PORT = int(os.environ.get("RUNTIME_PORT", "5001"))
INVOKE_PATH = os.environ.get("RUNTIME_PATH", "/invoke")

# Garante que a pasta do código (ex.: backend/src) esteja no sys.path para
# importar o módulo do handler como a Lambda real faz.
_TASK_ROOT_ABS = os.path.abspath(os.path.join(os.path.dirname(__file__), TASK_ROOT))
if _TASK_ROOT_ABS not in sys.path:
    sys.path.insert(0, _TASK_ROOT_ABS)


class _LambdaContext:
    """Reconstrói um objeto de context mínimo a partir do JSON recebido."""

    def __init__(self, data):
        data = data or {}
        self.aws_request_id = data.get("awsRequestId")
        self.function_name = data.get("functionName")
        self.function_version = data.get("functionVersion")
        self.invoked_function_arn = data.get("invokedFunctionArn")
        self.memory_limit_in_mb = data.get("memoryLimitInMB")
        self.log_group_name = data.get("logGroupName")
        self.log_stream_name = data.get("logStreamName")
        self._deadline_ms = data.get("deadlineMs")

    def get_remaining_time_in_millis(self):
        if self._deadline_ms is None:
            return 0
        import time

        return max(0, int(self._deadline_ms - time.time() * 1000))


def _load_handler(spec: str):
    """Importa 'modulo.funcao' e retorna a função handler."""
    if "." not in spec:
        raise ValueError(
            f"LAMBDA_HANDLER inválido: '{spec}'. Esperado formato 'modulo.funcao'."
        )
    module_name, func_name = spec.rsplit(".", 1)
    module = importlib.import_module(module_name)
    return getattr(module, func_name)


# Carrega o handler uma vez no boot (reuso entre invocações).
_handler = _load_handler(HANDLER_SPEC)


class RuntimeHandler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        # Health check simples.
        if self.path.rstrip("/") in ("", "/health"):
            self._send_json(200, {"status": "healthy", "handler": HANDLER_SPEC})
        else:
            self._send_json(404, {"errorMessage": f"Rota não encontrada: {self.path}"})

    def do_POST(self):
        if self.path.split("?")[0].rstrip("/") != INVOKE_PATH.rstrip("/"):
            self._send_json(404, {"errorMessage": f"Rota não encontrada: {self.path}"})
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            data = json.loads(raw.decode("utf-8") or "{}")
        except Exception as err:  # noqa: BLE001
            self._send_json(
                400,
                {"errorType": "InvalidRequest", "errorMessage": f"Body inválido: {err}"},
            )
            return

        event = data.get("event", {})
        context = _LambdaContext(data.get("context"))

        # Captura o stdout do handler para repassar como logs ao CloudWatch
        # simulado (envelope { result, logs }).
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                result = _handler(event, context)
            logs = [ln for ln in buf.getvalue().splitlines() if ln]
            self._send_json(200, {"result": result, "logs": logs})
        except Exception as err:  # noqa: BLE001
            logs = [ln for ln in buf.getvalue().splitlines() if ln]
            self._send_json(
                500,
                {
                    "errorType": type(err).__name__,
                    "errorMessage": str(err),
                    "stackTrace": traceback.format_exc().splitlines(),
                    "logs": logs,
                },
            )

    def log_message(self, fmt, *args):
        # Evita o log padrão barulhento do BaseHTTPRequestHandler.
        sys.stderr.write("[runtime] " + (fmt % args) + "\n")


def main():
    server = ThreadingHTTPServer((HOST, PORT), RuntimeHandler)
    print(
        f"Lambda runtime server ouvindo em http://{HOST}:{PORT}{INVOKE_PATH} "
        f"(handler: {HANDLER_SPEC}, task_root: {_TASK_ROOT_ABS})"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando runtime server...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
