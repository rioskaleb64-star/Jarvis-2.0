import os
if __name__ == "__main__":
    from instancia_util import reservar_instancia
    if not reservar_instancia("listener"):
        raise SystemExit(17)
import time
import difflib
import threading
import subprocess
import winsound
import pyaudiowpatch as pyaudio
import speech_recognition as sr
from PIL import Image, ImageDraw
import pystray
import sys
from mic_util import Microfone, MIC_DEVICE_INDEX, MIC_SAMPLE_RATE, MIC_CHUNK_SIZE, VAD_SILENCIO_LIMIAR, VAD_SILENCIO_MAXIMO, rms_audio
from wake_util import WakeWordLocal

from log_util import criar_logger

# Necessário para o SpeechRecognition conseguir usar o PyAudioWPatch
# em vez do PyAudio tradicional (que não compila em Python 3.14 sem
# o Visual C++ Build Tools instalado)
sr.Microphone.get_pyaudio = lambda self: pyaudio

# Hotkey global (Ctrl+Alt+J) é opcional — se o pacote "keyboard" não estiver
# instalado, o listener continua funcionando normalmente só por voz.
try:
    import keyboard
    _KEYBOARD_DISPONIVEL = True
except ImportError:
    _KEYBOARD_DISPONIVEL = False

# ================================
# CONFIGURAÇÃO
# ================================
PASTA_JARVIS = os.path.dirname(os.path.abspath(__file__))
PYTHON_EXE = "py"

ARQUIVO_SINAL_SAIR = os.path.join(PASTA_JARVIS, ".encerrar_definitivo")

# Configuração de microfone TESTADA E COMPROVADA nesta máquina via
# PyAudioWPatch. NÃO usar índices do sounddevice aqui — a numeração
# é diferente entre bibliotecas. NÃO tentar redescobrir automaticamente:
# WDM-KS (que aparecia como "melhor" candidato em buscas automáticas)
# não suporta streaming em modo blocking nesta máquina
# (erro PaErrorCode -9999/-9996).
LANGUAGE = "pt-BR"

VAD_DURACAO_MAXIMA = 10

WAKE_WORD = "jarvis"
FRASES_ACORDAR = [
    "acorda", "acordar", "desperta", "bom dia",
    "e aí", "eae", "eaew", "bora trampar", "bora trabalhar",
    "vamo trabalhar", "partiu", "vambora", "ativa", "acessa",
    "liga aí", "na área", "acorda logo", "levanta",
    "desperta aí", "chegou a hora",
]

# Apelidos que dispensam dizer "jarvis" — combinados com uma das
# FRASES_ACORDAR acima, ainda acordam o listener. Lista bem pessoal,
# edite à vontade conforme o que você realmente costuma falar.
APELIDOS_CARINHOSOS = [
    "merdinha", "bostinha", "seu inútil",
    "seu preguiçoso", "seu zé ruela", "parceiro", "companheiro",
]


def contem_apelido_carinhoso(texto):
    texto_lower = texto.lower()
    return any(apelido in texto_lower for apelido in APELIDOS_CARINHOSOS)

LOG_FILE = os.path.join(PASTA_JARVIS, "listener_log.txt")
log = criar_logger(LOG_FILE)

processo_jarvis = None
status_atual = "😴 Dormindo (diga 'Hey Jarvis' ou Ctrl+Alt+J)"

_microfone = Microfone(log)

# Evita que voz + hotkey acordem o Jarvis ao mesmo tempo por acidente
_LOCK_ACORDAR = threading.Lock()


def _beep_acordando():
    try:
        winsound.Beep(660, 150)
    except Exception:
        pass


# ============================================================
# MICROFONE — PyAudioWPatch, dispositivo fixo e testado (índice 1)
# STREAM PERSISTENTE: fica aberto entre uma frase e outra (evita o
# overhead de recriar o PyAudio a cada captura). É explicitamente
# FECHADO antes de abrir o Jarvis principal (pra não disputar o mesmo
# dispositivo de áudio com ele) e reaberto com retry/backoff depois
# que o Jarvis é encerrado.
# ============================================================
def _abrir_stream_persistente():
    return _microfone.abrir()


def _garantir_stream():
    return _microfone.garantir()


def fechar_stream_microfone():
    _microfone.fechar()


# ============================================================
# ÍCONES (gerados na hora, sem precisar de arquivo externo)
# ============================================================
def criar_icone(cor):
    img = Image.new('RGB', (64, 64), color=(30, 30, 30))
    draw = ImageDraw.Draw(img)
    draw.ellipse((8, 8, 56, 56), fill=cor)
    return img


ICONE_DORMINDO = criar_icone((80, 80, 220))
ICONE_ACORDADO = criar_icone((80, 200, 100))


# ============================================================
# CAPTURA DE ÁUDIO COM VAD (usando PyAudioWPatch, stream persistente)
# ============================================================
def escutar_frase():
    if not _garantir_stream():
        time.sleep(1.0)
        return None

    recognizer = sr.Recognizer()
    block_duration = MIC_CHUNK_SIZE / MIC_SAMPLE_RATE

    frames_gravados = []
    silencio_acumulado = 0.0
    tempo_total = 0.0
    comecou_a_falar = False

    while True:
        try:
            dados = _microfone.stream.read(MIC_CHUNK_SIZE, exception_on_overflow=False)
        except Exception as e:
            log(f"Erro lendo do microfone: {e}")
            fechar_stream_microfone()
            return None

        rms = rms_audio(dados)
        tempo_total += block_duration

        if rms > _microfone.limiar_vad:
            comecou_a_falar = True
            silencio_acumulado = 0.0
            frames_gravados.append(dados)
        else:
            silencio_acumulado += block_duration
            if comecou_a_falar:
                frames_gravados.append(dados)
            if silencio_acumulado >= VAD_SILENCIO_MAXIMO:
                break

        if tempo_total >= VAD_DURACAO_MAXIMA:
            break

    if not frames_gravados:
        return None

    audio_bytes = b"".join(frames_gravados)

    try:
        audio = sr.AudioData(audio_bytes, MIC_SAMPLE_RATE, 2)
        return recognizer.recognize_google(audio, language=LANGUAGE)
    except sr.UnknownValueError:
        return None
    except sr.RequestError as e:
        log(f"Erro no reconhecimento (precisa de internet): {e}")
        return None


def contem_wake_word(texto):
    palavras = [p.strip(",.!?;:") for p in texto.lower().split()]
    for p in palavras:
        if difflib.get_close_matches(p, [WAKE_WORD], n=1, cutoff=0.6):
            return True
    return False


def contem_frase_acordar(texto):
    texto_lower = texto.lower()
    return any(frase in texto_lower for frase in FRASES_ACORDAR)


# ============================================================
# ACORDAR O JARVIS PRINCIPAL
# ============================================================
def acordar_jarvis(icone, modo_texto=False):
    global processo_jarvis, status_atual

    if not _LOCK_ACORDAR.acquire(blocking=False):
        log("⚠️ Ativação já em andamento, ignorando chamada duplicada.")
        return

    try:
        log("🌅 Ativação detectada! Abrindo o Jarvis...")
        _beep_acordando()
        status_atual = "🟢 Acordado (Jarvis rodando)"
        icone.icon = ICONE_ACORDADO
        icone.title = "Jarvis - Acordado"
        icone.update_menu()

        fechar_stream_microfone()

        caminho_crash_log = os.path.join(PASTA_JARVIS, "jarvis_crash.log")
        try:
            with open(caminho_crash_log, "w", encoding="utf-8") as arquivo_crash:
                processo_jarvis = subprocess.Popen(
                    [_caminho_pythonw(), "jarvis.py"] + (["--texto"] if modo_texto else []),
                    cwd=PASTA_JARVIS,
                    stdout=arquivo_crash,
                    stderr=subprocess.STDOUT,
                )
                processo_jarvis.wait()

            # Se o processo morreu rápido demais, quase certamente crashou
            if processo_jarvis.returncode != 0:
                log(f"⚠️ jarvis.py encerrou com código {processo_jarvis.returncode} "
                    f"— veja jarvis_crash.log para detalhes.")
        except Exception as e:
            log(f"Erro ao iniciar o Jarvis: {e}")

        log("💤 Jarvis principal encerrado. Voltando a dormir.")
        status_atual = "😴 Dormindo (diga 'Hey Jarvis' ou Ctrl+Alt+J)"
        icone.icon = ICONE_DORMINDO
        icone.title = "Jarvis - Dormindo"
        icone.update_menu()

        for tentativa in range(1, 6):
            if _abrir_stream_persistente():
                return
            log(f"⏳ Tentativa {tentativa}/5 de reabrir o microfone falhou, aguardando...")
            time.sleep(tentativa * 1.0)

        log("❌ Não consegui reabrir o microfone depois de várias tentativas.")
    finally:
        _LOCK_ACORDAR.release()

def _caminho_pythonw():
    python_exe = sys.executable
    pasta = os.path.dirname(python_exe)
    candidato = os.path.join(pasta, "pythonw.exe")
    if os.path.exists(candidato):
        return candidato
    return python_exe


# ============================================================
# LOOP PRINCIPAL DE ESCUTA
# ============================================================
def loop_escuta(icone):
    log("👂 Listener iniciado. Diga 'Hey Jarvis' ou aperte Ctrl+Alt+J quando quiser.")

    try:
        detector = WakeWordLocal()
        log("✅ Wake word local ativa. Diga 'Hey Jarvis'.")
    except Exception as exc:
        detector = None
        log(f"⚠️ Wake word local indisponível: {exc}")

    if detector:
        while True:
            if _LOCK_ACORDAR.locked():
                time.sleep(0.2)
                continue
            if not _garantir_stream():
                time.sleep(1)
                continue
            try:
                # Blocos exatos de 80 ms para openWakeWord.
                dados = _microfone.stream.read(3528, exception_on_overflow=False)
                if detector.detectar(dados):
                    detector.resetar()
                    acordar_jarvis(icone)
            except Exception as exc:
                if not _LOCK_ACORDAR.locked():
                    log(f"Falha na detecção local: {exc}")
                    fechar_stream_microfone()
                time.sleep(1)
        return

    if os.getenv("JARVIS_CLOUD_WAKE_FALLBACK") != "1":
        log("Ativação por voz desativada até instalar openWakeWord; Ctrl+Alt+J continua disponível.")
        return

    while True:
        if _LOCK_ACORDAR.locked():
            time.sleep(0.2)
            continue
        texto = escutar_frase()
        if not texto:
            continue

        log(f"Ouvido: {texto}")

        if (contem_wake_word(texto) or contem_apelido_carinhoso(texto)) and contem_frase_acordar(texto):
           acordar_jarvis(icone)


# ============================================================
# HOTKEY GLOBAL (Ctrl+Alt+J) — alternativa à ativação por voz
# ============================================================
def _registrar_hotkey(icone):
    if not _KEYBOARD_DISPONIVEL:
        log("ℹ️ Pacote 'keyboard' não instalado — hotkey Ctrl+Alt+J desativado (só ativação por voz).")
        return
    try:
        keyboard.add_hotkey('ctrl+alt+j', lambda: threading.Thread(
    target=acordar_jarvis, args=(icone,), daemon=True
        ).start())
        log("⌨️ Hotkey Ctrl+Alt+J registrado.")
    except Exception as e:
        log(f"⚠️ Não consegui registrar o hotkey Ctrl+Alt+J (tente rodar como administrador): {e}")


# ============================================================
# MENU DA BANDEJA
# ============================================================
def on_sair(icone, item):
    log("Encerrando o listener (menu 'Sair completamente').")
    try:
        with open(ARQUIVO_SINAL_SAIR, "w", encoding="utf-8") as f:
            f.write("sair")
    except Exception:
        pass
    fechar_stream_microfone()
    icone.stop()
    os._exit(0)


def criar_menu():
    return pystray.Menu(
        pystray.MenuItem(lambda item: status_atual, lambda icone, item: None, enabled=False),
        pystray.MenuItem("Abrir modo texto", lambda icone, item: threading.Thread(
            target=acordar_jarvis, args=(icone, True), daemon=True).start()),
        pystray.MenuItem("Sair completamente", on_sair)
    )


def main():
    log("Testando acesso ao microfone (PyAudioWPatch, índice fixo)...")
    if not _abrir_stream_persistente():
        log("❌ Listener não conseguiu acessar o microfone.")
        return

    log(f"🎙️ Pronto para ouvir: dispositivo {MIC_DEVICE_INDEX}, {MIC_SAMPLE_RATE} Hz")

    icone = pystray.Icon("jarvis_listener", ICONE_DORMINDO, "Jarvis - Dormindo", criar_menu())

    _registrar_hotkey(icone)

    thread = threading.Thread(target=loop_escuta, args=(icone,), daemon=True)
    thread.start()

    icone.run()


if __name__ == "__main__":
    main()
