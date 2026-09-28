from __future__ import annotations

import json
import os
import threading
import time
import uuid
from typing import Any

try:
    from websockets.sync.server import serve
except ImportError as exc:
    raise RuntimeError(
        "A integração do navegador precisa do pacote 'websockets'. "
        "Instale com: py -m pip install websockets"
    ) from exc


HOST = "127.0.0.1"
# O HUD usa 8765. A extensão precisa de uma porta exclusiva.
PORT = int(os.getenv("JARVIS_BROWSER_PORT", "8766"))

# Troque este valor nos DOIS lugares se quiser usar outro token:
#   1) browser_bridge.py
#   2) extensao_jarvis/background.js
TOKEN = os.getenv("JARVIS_BROWSER_TOKEN", "jarvis-local-bridge-v1-9f7d3a")

_connection = None
_connection_lock = threading.Lock()
_send_lock = threading.Lock()
_server_started = False
_server_start_lock = threading.Lock()
_connected_event = threading.Event()
_server_error = None
_server_ready = threading.Event()

_pending: dict[str, dict[str, Any]] = {}
_pending_lock = threading.Lock()


def _safe_send(ws, payload: dict[str, Any]) -> None:
    with _send_lock:
        ws.send(json.dumps(payload, ensure_ascii=False))


def _handler(ws) -> None:
    """Recebe a conexão da extensão Chromium."""
    global _connection

    try:
        # Sites comuns não podem controlar o navegador por um WebSocket local.
        origem = ws.request.headers.get("Origin", "")
        if origem and not origem.startswith("chrome-extension://"):
            ws.close(code=1008, reason="extension origin required")
            return
        raw = ws.recv(timeout=5)
        hello = json.loads(raw)

        if not isinstance(hello, dict) or hello.get("type") != "hello" or hello.get("token") != TOKEN:
            ws.close(code=1008, reason="unauthorized")
            return

        with _connection_lock:
            old = _connection
            _connection = ws
            _connected_event.set()

        if old is not None and old is not ws:
            try:
                old.close(code=1000, reason="new connection")
            except Exception:
                pass

        _safe_send(ws, {"type": "hello_ack", "ok": True})

        for raw in ws:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if not isinstance(msg, dict):
                continue
            msg_type = msg.get("type")

            if msg_type == "keepalive":
                _safe_send(ws, {"type": "keepalive_ack"})
                continue

            if msg_type == "response":
                request_id = msg.get("request_id")
                if not request_id:
                    continue

                with _pending_lock:
                    pending = _pending.get(request_id)

                if pending and pending.get("connection") is ws:
                    pending["response"] = msg
                    pending["event"].set()

    except Exception:
        pass
    finally:
        with _connection_lock:
            if _connection is ws:
                _connection = None
                _connected_event.clear()
        with _pending_lock:
            for pending in _pending.values():
                if pending.get("connection") is ws:
                    pending["event"].set()


def _server_main() -> None:
    global _server_error
    try:
        with serve(_handler, HOST, PORT, max_size=256000) as server:
            _server_ready.set()
            server.serve_forever()
    except OSError as exc:
        _server_error = f"Não foi possível abrir a ponte Brave na porta {PORT}: {exc}"
        _server_ready.set()


def start_browser_bridge() -> None:
    """Inicia o servidor local uma única vez, em thread daemon."""
    global _server_started

    with _server_start_lock:
        if _server_started:
            return

        thread = threading.Thread(
            target=_server_main,
            name="JarvisBrowserBridge",
            daemon=True,
        )
        thread.start()
        _server_started = True

    _server_ready.wait(timeout=1)


def browser_connected() -> bool:
    start_browser_bridge()
    return _connected_event.is_set()


def browser_command(action: str, timeout: float = 5.0, **params: Any) -> dict[str, Any]:
    """Envia um comando à extensão e espera a resposta."""
    start_browser_bridge()

    if _server_error:
        return {"ok": False, "error": _server_error}
    if not _connected_event.wait(timeout=min(timeout, 2.0)):
        return {
            "ok": False,
            "error": (
                "A extensão JARVIS Browser Bridge não está conectada. "
                "Abra o navegador com a extensão carregada e tente novamente."
            ),
        }

    request_id = uuid.uuid4().hex
    event = threading.Event()

    with _connection_lock:
        ws = _connection
    with _pending_lock:
        _pending[request_id] = {
            "event": event,
            "response": None,
            "connection": ws,
        }

    try:
        if ws is None:
            return {"ok": False, "error": "A conexão com o navegador caiu."}

        try:
            _safe_send(
                ws,
                {
                    "type": "command",
                    "request_id": request_id,
                    "action": action,
                    "params": params,
                },
            )
        except Exception:
            return {"ok": False, "error": "Não foi possível enviar o comando ao navegador."}

        if not event.wait(timeout=timeout):
            return {"ok": False, "error": "O navegador demorou demais para responder."}

        with _pending_lock:
            response = _pending[request_id].get("response")

        if not response:
            return {"ok": False, "error": "Resposta vazia do navegador."}

        return {
            key: value
            for key, value in response.items()
            if key not in {"type", "request_id"}
        }

    finally:
        with _pending_lock:
            _pending.pop(request_id, None)


# Pode ser importado pelo JARVIS sem bloquear o processo principal.
start_browser_bridge()
