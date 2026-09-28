import asyncio
import json
import threading
import websockets
import secrets

_loop = None
_clientes = set()
_lock = threading.Lock()
_callback_comando = None
TOKEN_SESSAO = secrets.token_urlsafe(32)
_iniciado = False
_pronto = threading.Event()
_erro = None


def registrar_callback_comando(func):
    """jarvis.py chama isso pra receber comandos vindos do HUD (botões, texto, etc)."""
    global _callback_comando
    _callback_comando = func


async def _handler(websocket):
    autorizado = False
    try:
        async for mensagem in websocket:
            try:
                dados = json.loads(mensagem)
            except json.JSONDecodeError:
                continue
            if not isinstance(dados, dict):
                continue
            if not isinstance(dados.get("token"), str) or not secrets.compare_digest(dados["token"], TOKEN_SESSAO):
                await websocket.close(code=1008, reason="session required")
                return
            if not autorizado:
                with _lock:
                    _clientes.add(websocket)
                autorizado = True
            if dados.get("tipo") == "comando" and _callback_comando:
                try:
                    await asyncio.to_thread(_callback_comando, dados.get("valor"), dados.get("payload"))
                except Exception as exc:
                    await websocket.send(json.dumps({"tipo": "log", "quem": "sistema", "texto": f"Não consegui processar esse comando: {exc}"}, ensure_ascii=False))
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        with _lock:
            _clientes.discard(websocket)


async def _broadcast_async(mensagem: dict):
    if not _clientes:
        return
    texto = json.dumps(mensagem, ensure_ascii=False)
    mortos = []
    for cliente in list(_clientes):
        try:
            await cliente.send(texto)
        except Exception:
            mortos.append(cliente)
    for m in mortos:
        _clientes.discard(m)


def enviar(mensagem: dict):
    """Thread-safe. Pode ser chamado de qualquer thread (voz, IA, etc)."""
    loop = _loop
    if loop is None or loop.is_closed():
        return
    tarefa = _broadcast_async(mensagem)
    try:
        asyncio.run_coroutine_threadsafe(tarefa, loop)
    except RuntimeError:
        # O servidor pode encerrar entre a checagem e o agendamento.
        tarefa.close()


async def _main(host, port):
    global _loop
    async with websockets.serve(_handler, host, port, max_size=32000):
        _loop = asyncio.get_running_loop()
        _pronto.set()
        try:
            await asyncio.Future()
        finally:
            _loop = None


def iniciar_servidor(host="localhost", port=8765):
    global _iniciado
    with _lock:
        if _iniciado:
            return
        _iniciado = True
    def _run():
        global _erro
        try:
            asyncio.run(_main(host, port))
        except OSError as exc:
            _erro = f"HUD não conseguiu abrir {host}:{port}. Feche outra instância do JARVIS. {exc}"
            _pronto.set()
    threading.Thread(target=_run, daemon=True).start()
    if not _pronto.wait(3):
        raise RuntimeError("O servidor da interface demorou para iniciar.")
    if _erro:
        raise RuntimeError(_erro)


def tem_clientes():
    with _lock:
        return bool(_clientes)
