"""Voz local selecionável: vozes do Windows ou modelos Piper já baixados."""
import io
import os
from pathlib import Path
import queue
import threading
import wave
import winsound

from armazenamento import obter_agenda


class VozPiper:
    # Nome preservado para compatibilidade com o restante do projeto.
    def __init__(self, logger):
        self.logger = logger
        self.modelo = os.getenv("PIPER_VOICE_MODEL", "")
        padrao = "piper:" + str(Path(self.modelo).resolve()) if self.modelo and Path(self.modelo).is_file() else "windows:padrao"
        self.escolhida = obter_agenda().configuracao("voz_escolhida", padrao)
        self.velocidade = obter_agenda().configuracao("voz_velocidade", 0)
        self.ativa = obter_agenda().configuracao("voz_ativa", bool(self.modelo))
        self.falando = threading.Event()
        self._fila = queue.Queue(maxsize=4)
        self._geracao = 0
        self._voz = None
        self._modelo_carregado = None
        self._thread = None
        self._lock = threading.Lock()

    def opcoes(self):
        itens = [{"id": "windows:padrao", "nome": "Windows · voz padrão (offline)"}]
        try:
            import pythoncom
            from win32com.client import Dispatch
            pythoncom.CoInitialize()
            try:
                for voz in Dispatch("SAPI.SpVoice").GetVoices():
                    itens.append({"id": "windows:" + voz.Id, "nome": "Windows · " + voz.GetDescription()})
            finally:
                pythoncom.CoUninitialize()
        except Exception as exc:
            self.logger(f"Não foi possível listar as vozes Windows: {exc}")
        modelos = list((Path(__file__).resolve().parent / "vozes").glob("*.onnx"))[:30]
        if self.modelo and Path(self.modelo).is_file():
            modelos.append(Path(self.modelo))
        vistos = set()
        for modelo in modelos:
            caminho = str(modelo.resolve())
            if caminho not in vistos and Path(caminho + ".json").is_file():
                vistos.add(caminho)
                itens.append({"id": "piper:" + caminho, "nome": "Piper · " + modelo.stem})
        return itens

    def selecionar(self, identificador):
        if identificador not in {item['id'] for item in self.opcoes()}:
            return "Voz não encontrada. Atualize a lista ou baixe o modelo Piper e seu .onnx.json."
        self.parar()
        self.escolhida = identificador
        obter_agenda().configurar("voz_escolhida", identificador)
        return "Voz selecionada. Use Ouvir amostra para experimentar."

    def ajustar_velocidade(self, valor):
        if type(valor) is not int or not -4 <= valor <= 4:
            raise ValueError("Velocidade deve estar entre -4 e 4.")
        self.velocidade = valor
        obter_agenda().configurar("voz_velocidade", valor)

    def alternar(self):
        self.ativa = not self.ativa
        obter_agenda().configurar("voz_ativa", self.ativa)
        if not self.ativa:
            self.parar()
        return "Resposta falada ativada." if self.ativa else "Resposta falada desativada."

    def parar(self):
        self._geracao += 1
        while True:
            try:
                self._fila.get_nowait()
            except queue.Empty:
                break
        try:
            winsound.PlaySound(None, 0)
        except RuntimeError:
            pass

    def falar(self, texto, forcar=False):
        if not texto or not (self.ativa or forcar):
            return
        with self._lock:
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._trabalhar, daemon=True, name="JarvisVoz")
                self._thread.start()
        try:
            self._fila.put_nowait((str(texto)[:1200], self._geracao, forcar))
        except queue.Full:
            self.logger("Fila de voz cheia; a resposta continua disponível no texto.")

    def _trabalhar(self):
        while True:
            texto, geracao, forcar = self._fila.get()
            if geracao != self._geracao or not (self.ativa or forcar):
                continue
            self.falando.set()
            try:
                if self.escolhida.startswith("piper:"):
                    self._falar_piper(texto, geracao, forcar)
                else:
                    self._falar_windows(texto, geracao, forcar)
            except Exception as exc:
                self.logger(f"Falha na resposta falada: {exc}. Selecione outra voz na Central.")
            finally:
                self.falando.clear()

    def _falar_windows(self, texto, geracao, forcar):
        import pythoncom
        from win32com.client import Dispatch
        pythoncom.CoInitialize()
        try:
            voz = Dispatch("SAPI.SpVoice")
            identificador = self.escolhida.removeprefix("windows:")
            if identificador != "padrao":
                alternativas = [v for v in voz.GetVoices() if v.Id == identificador]
                if not alternativas:
                    raise ValueError("A voz selecionada não está mais instalada")
                voz.Voice = alternativas[0]
            voz.Rate = self.velocidade
            voz.Speak(texto, 1 | 16)  # assíncrono e texto literal (não XML)
            while not voz.WaitUntilDone(50):
                if geracao != self._geracao or not (self.ativa or forcar):
                    voz.Speak("", 2)
                    break
                pythoncom.PumpWaitingMessages()
        finally:
            pythoncom.CoUninitialize()

    def _falar_piper(self, texto, geracao, forcar):
        modelo = self.escolhida.removeprefix("piper:")
        if self._voz is None or self._modelo_carregado != modelo:
            from piper import PiperVoice
            self._voz = PiperVoice.load(modelo)
            self._modelo_carregado = modelo
        memoria = io.BytesIO()
        with wave.open(memoria, "wb") as wav:
            self._voz.synthesize_wav(texto, wav)
        if geracao == self._geracao and (self.ativa or forcar):
            winsound.PlaySound(memoria.getvalue(), winsound.SND_MEMORY)
