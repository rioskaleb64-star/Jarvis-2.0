"""Impede duas cópias do mesmo componente de disputar áudio e portas."""
import ctypes
from ctypes import wintypes
import os

_handles = []


def reservar_instancia(componente):
    if os.name != "nt":
        return True
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.CreateMutexW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateMutexW(None, False, "Local\\Jarvis2_" + componente)
    erro = ctypes.get_last_error()
    if not handle:
        raise OSError(erro, "Não foi possível reservar a instância do JARVIS")
    if erro == 183:
        kernel.CloseHandle(handle)
        return False
    _handles.append(handle)
    return True
