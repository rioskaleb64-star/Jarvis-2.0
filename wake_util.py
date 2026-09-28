"""Detector de wake word offline para PCM 44,1 kHz do microfone configurado."""
import os

import numpy as np


class WakeWordLocal:
    def __init__(self):
        from openwakeword import Model, MODELS, FEATURE_MODELS
        necessarios = [MODELS["hey_jarvis"]["model_path"].replace(".tflite", ".onnx")]
        necessarios.extend(info["model_path"].replace(".tflite", ".onnx")
                           for info in FEATURE_MODELS.values())
        if any(not os.path.isfile(caminho) for caminho in necessarios):
            raise RuntimeError("Modelos openWakeWord ausentes; execute uma vez: python -c \"import openwakeword.utils; openwakeword.utils.download_models(model_names=['hey_jarvis_v0.1'])\"")
        self.modelo = Model(wakeword_models=[necessarios[0]], inference_framework="onnx")

    def detectar(self, dados_44100):
        amostras = np.frombuffer(dados_44100, dtype=np.int16)
        # 3.528 amostras a 44,1 kHz = 80 ms = 1.280 amostras a 16 kHz.
        audio = np.interp(np.linspace(0, len(amostras) - 1, 1280),
                          np.arange(len(amostras)), amostras).astype(np.int16)
        pontuacoes = self.modelo.predict(audio)
        return any("jarvis" in nome.lower() and valor >= 0.5
                   for nome, valor in pontuacoes.items())

    def resetar(self):
        self.modelo.reset()
