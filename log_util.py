import os
import sys
import time

TAMANHO_MAXIMO_LOG = 2 * 1024 * 1024  # 2 MB antes de rotacionar


def _rotacionar_se_precisar(caminho_log):
    try:
        if os.path.exists(caminho_log) and os.path.getsize(caminho_log) > TAMANHO_MAXIMO_LOG:
            caminho_antigo = caminho_log + ".old"
            if os.path.exists(caminho_antigo):
                os.remove(caminho_antigo)
            os.rename(caminho_log, caminho_antigo)
    except Exception:
        pass


def criar_logger(caminho_log):
    def log(msg):
        linha = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"

        # Sob pythonw.exe (sem console), sys.stdout é None — chamar
        # print() nesse caso lança AttributeError e derruba o programa
        # inteiro. Esse guard evita isso.
        try:
            if sys.stdout is not None:
                print(linha)
        except Exception:
            pass

        try:
            _rotacionar_se_precisar(caminho_log)
            with open(caminho_log, "a", encoding="utf-8") as f:
                f.write(linha + "\n")
        except Exception:
            pass

    return log