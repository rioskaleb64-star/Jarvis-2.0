"""Captura de microfone compartilhada pelo listener e pelo Jarvis."""
import time

import numpy as np
import pyaudiowpatch as pyaudio

MIC_DEVICE_INDEX = 1
MIC_SAMPLE_RATE = 44100
MIC_CHUNK_SIZE = 1024
VAD_SILENCIO_LIMIAR = 500
VAD_SILENCIO_MAXIMO = 0.7


class Microfone:
    def __init__(self, logger, fator_ruido=3.0):
        self.logger = logger
        self.fator_ruido = fator_ruido
        self.instancia = None
        self.stream = None
        self.limiar_vad = VAD_SILENCIO_LIMIAR

    def abrir(self):
        if self.stream is not None:
            return True
        try:
            self.instancia = pyaudio.PyAudio()
            self.stream = self.instancia.open(
                format=pyaudio.paInt16, channels=1, rate=MIC_SAMPLE_RATE,
                input=True, input_device_index=MIC_DEVICE_INDEX,
                frames_per_buffer=MIC_CHUNK_SIZE,
            )
            # Um segundo de ruído de fundo. A mediana evita que um estalo
            # isolado aumente demais o limiar da sessão.
            amostras = []
            ate = time.monotonic() + 1.0
            while time.monotonic() < ate:
                dados = self.stream.read(MIC_CHUNK_SIZE, exception_on_overflow=False)
                amostras.append(rms_audio(dados))
            base = float(np.median(amostras)) if amostras else 0.0
            self.limiar_vad = max(VAD_SILENCIO_LIMIAR, base * self.fator_ruido)
            self.logger(f"Microfone pronto; ruído base {base:.0f}, limiar VAD {self.limiar_vad:.0f}.")
            return True
        except Exception as exc:
            self.logger(f"Não consegui abrir o microfone (índice {MIC_DEVICE_INDEX}): {exc}")
            self.fechar()
            return False

    def garantir(self):
        return self.stream is not None or self.abrir()

    def fechar(self):
        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
        except Exception:
            pass
        try:
            if self.instancia:
                self.instancia.terminate()
        except Exception:
            pass
        self.stream = None
        self.instancia = None


def rms_audio(dados):
    bloco = np.frombuffer(dados, dtype=np.int16).astype(np.float32)
    return float(np.sqrt(np.mean(bloco ** 2))) if bloco.size else 0.0
