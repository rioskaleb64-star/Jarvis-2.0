"""
Watchdog opcional do listener.

Em vez de rodar "pythonw jarvis_listener.py" direto (por exemplo, na
inicialização do Windows), rode "pythonw jarvis_watchdog.py". Ele cuida
de (re)lançar o listener sozinho se o processo cair de forma inesperada
(crash, erro não tratado, etc).

Pra encerrar TUDO de propósito, sem o watchdog reabrir o listener em
seguida, use o item "Sair completamente" do menu da bandeja — ele deixa
um arquivo de sinal (.encerrar_definitivo) avisando o watchdog pra
também parar.

Isso é 100% opcional: se você preferir continuar rodando o
jarvis_listener.py direto como antes, esse arquivo simplesmente não é
usado e não muda nada no comportamento existente.
"""
import os
import time
import subprocess
import sys

PASTA_JARVIS = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_SINAL_SAIR = os.path.join(PASTA_JARVIS, ".encerrar_definitivo")
ESPERA_ENTRE_TENTATIVAS = 3  # segundos


def _caminho_pythonw():
    candidato = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return candidato if os.path.exists(candidato) else sys.executable


def main():
    # Limpa qualquer sinal de uma execução anterior antes de começar
    if os.path.exists(ARQUIVO_SINAL_SAIR):
        os.remove(ARQUIVO_SINAL_SAIR)

    while True:
        print("Watchdog: iniciando jarvis_listener.py...")
        processo = subprocess.Popen([_caminho_pythonw(), "jarvis_listener.py"], cwd=PASTA_JARVIS)
        processo.wait()

        if processo.returncode == 17:
            print("Watchdog: já existe um listener aberto. Encerrando esta cópia.")
            break

        if os.path.exists(ARQUIVO_SINAL_SAIR):
            os.remove(ARQUIVO_SINAL_SAIR)
            print("Watchdog: encerramento definitivo solicitado pelo menu. Parando.")
            break

        print(f"Watchdog: o listener caiu inesperadamente. Reabrindo em {ESPERA_ENTRE_TENTATIVAS}s...")
        time.sleep(ESPERA_ENTRE_TENTATIVAS)


if __name__ == "__main__":
    main()
