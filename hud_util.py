"""Saída do Jarvis: log em arquivo + eventos pro HUD.

Este arquivo existe porque é o ÚNICO pedaço compartilhado entre o
``jarvis.py`` (loop de voz, interface) e o ``ferramentas.py`` (avisar
erros, progresso do escaneamento de apps). Os dois precisam das mesmas
funções, então elas moram num lugar só em vez de duplicadas.
"""
import os
import queue
import time
import threading
from collections import deque

import hud_bridge
from log_util import criar_logger

PASTA_JARVIS = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(PASTA_JARVIS, "jarvis_log.txt")

log = criar_logger(LOG_FILE)

# Fila interna de eventos (mantida por compatibilidade)
EVENTOS = queue.Queue(maxsize=128)
_logs = deque(maxlen=100)
_logs_lock = threading.Lock()


def texto_status_para_estado_hud(texto_status):
    if "Ouvindo" in texto_status:
        return "ouvindo"
    if "Processando" in texto_status:
        return "processando"
    if "Pausado" in texto_status:
        return "dormindo"
    return "dormindo"


def emitir(tipo, **kwargs):
    try:
        EVENTOS.put_nowait((tipo, kwargs))
    except queue.Full:
        try:
            EVENTOS.get_nowait()
        except queue.Empty:
            pass
        try:
            EVENTOS.put_nowait((tipo, kwargs))
        except queue.Full:
            pass

    if tipo == "status":
        estado = texto_status_para_estado_hud(kwargs.get("texto", ""))
        hud_bridge.enviar({"tipo": "estado", "valor": estado})
    elif tipo == "log":
        with _logs_lock:
            _logs.append({"quem": kwargs.get("quem", "sistema"), "texto": str(kwargs.get("texto", ""))})
        hud_bridge.enviar({
            "tipo": "log",
            "quem": kwargs.get("quem", "sistema"),
            "texto": kwargs.get("texto", "")
        })
    elif tipo in {"config", "painel", "historico", "vozes", "confirmacao", "lembrete", "atividade"}:
        hud_bridge.enviar({"tipo": tipo, **kwargs})


def ultimos_logs():
    with _logs_lock:
        return list(_logs)


def emitir_audio(nivel):
    """Nível do microfone em tempo real (pulso visual do HUD)."""
    hud_bridge.enviar({"tipo": "audio", "valor": nivel})


def logar_e_emitir(texto, quem="sistema"):
    """Grava no jarvis_log.txt E mostra no HUD — usado pra eventos que
    valem a pena persistir em disco (erros, avisos, eventos de sistema)."""
    log(texto)
    emitir("log", quem=quem, texto=texto)


def iniciar_hud():
    hud_bridge.iniciar_servidor()


def registrar_comandos(callback):
    hud_bridge.registrar_callback_comando(callback)
