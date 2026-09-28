"""Diagnóstico sem iniciar HUD, microfone, voz ou ações no computador."""
import ast
import importlib.util
import json
import os
from pathlib import Path
import platform
import socket
import sys


RAIZ = Path(__file__).resolve().parent
DEPENDENCIAS = {
    "openai": "openai", "websockets": "websockets", "webview": "pywebview",
    "psutil": "psutil", "pythoncom": "pywin32", "pyautogui": "pyautogui",
    "pycaw": "pycaw", "comtypes": "comtypes", "numpy": "numpy",
    "pyaudiowpatch": "PyAudioWPatch", "speech_recognition": "SpeechRecognition",
    "keyboard": "keyboard", "pystray": "pystray", "PIL": "Pillow", "pyperclip": "pyperclip",
}


def main():
    print(f"JARVIS — diagnóstico local\nPython {platform.python_version()}\n{sys.executable}\n")
    ausentes = [pacote for modulo, pacote in DEPENDENCIAS.items() if importlib.util.find_spec(modulo) is None]
    if ausentes:
        print("Pacotes necessários ausentes: " + ", ".join(ausentes))
        print(f'Instale com: "{sys.executable}" -m pip install ' + " ".join(ausentes))
    else:
        print("✓ Dependências principais encontradas.")
    erros = []
    for arquivo in RAIZ.glob("*.py"):
        if arquivo.name.endswith("_backup.py"):
            continue
        try:
            ast.parse(arquivo.read_text(encoding="utf-8-sig"), filename=arquivo.name)
        except (SyntaxError, UnicodeError) as exc:
            erros.append(f"{arquivo.name}: {exc}")
    print("\n".join(erros) if erros else "✓ Sintaxe de todos os módulos Python válida.")
    for chave in ("GROQ_API_KEY", "OPENROUTER_API_KEY", "TAVILY_API_KEY"):
        print(f"{chave}: {'configurada' if os.getenv(chave) else 'não configurada'}")
    for porta, nome in ((8765, "HUD"), (int(os.getenv("JARVIS_BROWSER_PORT", "8766")), "Brave")):
        with socket.socket() as s:
            s.settimeout(.3)
            ocupada = s.connect_ex(("127.0.0.1", porta)) == 0
        print(f"{nome} / porta {porta}: {'ocupada (normal se o JARVIS estiver aberto)' if ocupada else 'livre'}")
    modelo = os.getenv("PIPER_VOICE_MODEL", "")
    print("Piper via ambiente: " + ("modelo encontrado" if modelo and Path(modelo).is_file() else "sem modelo; vozes do Windows disponíveis na Central"))
    manifesto = json.loads((RAIZ / "extensao_jarvis" / "manifest.json").read_text(encoding="utf-8"))
    print("Extensão Brave: versão " + manifesto["version"] + ". Recarregue em brave://extensions após atualizar.")
    print("\nLogs: jarvis_log.txt, jarvis_crash.log e listener_log.txt")
    return 1 if erros or ausentes else 0


if __name__ == "__main__":
    raise SystemExit(main())
