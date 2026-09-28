"""Registro único e validação dos argumentos antes de uma ferramenta agir."""
from copy import deepcopy
import json
import math

FUNCOES_DISPONIVEIS = {}
TOOLS = []


def ferramenta(descricao, parametros=None):
    def decorador(func):
        nome = func.__name__
        esquema = deepcopy(parametros or {"type": "object", "properties": {}})
        esquema.setdefault("additionalProperties", False)
        FUNCOES_DISPONIVEIS[nome] = func
        TOOLS[:] = [t for t in TOOLS if t["function"]["name"] != nome]
        TOOLS.append({"type": "function", "function": {
            "name": nome, "description": descricao, "parameters": esquema}})
        return func
    return decorador


def validar(valor, esquema, campo="argumentos"):
    tipo = esquema.get("type")
    tipos = {"string": lambda v: isinstance(v, str),
             "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
             "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v),
             "boolean": lambda v: isinstance(v, bool),
             "object": lambda v: isinstance(v, dict), "array": lambda v: isinstance(v, list)}
    if tipo in tipos and not tipos[tipo](valor):
        raise ValueError(f"{campo}: esperado {tipo}.")
    if "enum" in esquema and valor not in esquema["enum"]:
        raise ValueError(f"{campo}: escolha entre {', '.join(map(str, esquema['enum']))}.")
    if tipo == "string" and len(valor) > esquema.get("maxLength", 12000):
        raise ValueError(f"{campo}: texto longo demais.")
    if tipo in {"number", "integer"}:
        if valor < esquema.get("minimum", -math.inf) or valor > esquema.get("maximum", math.inf):
            raise ValueError(f"{campo}: número fora do intervalo permitido.")
    if tipo == "object":
        props = esquema.get("properties", {})
        faltantes = set(esquema.get("required", [])) - set(valor)
        extras = set(valor) - set(props)
        if faltantes:
            raise ValueError("Informe: " + ", ".join(sorted(faltantes)))
        if extras and not esquema.get("additionalProperties", False):
            raise ValueError("Parâmetros desconhecidos: " + ", ".join(sorted(extras)))
        for chave, item in valor.items():
            if chave in props:
                validar(item, props[chave], chave)
    if tipo == "array":
        if len(valor) > esquema.get("maxItems", 100):
            raise ValueError(f"{campo}: itens demais.")
        for item in valor:
            validar(item, esquema.get("items", {}), campo)


def executar_ferramenta(nome, argumentos):
    funcao = FUNCOES_DISPONIVEIS.get(nome)
    if funcao is None:
        return f"❌ Ferramenta desconhecida: {nome}."
    try:
        esquema = next(t["function"]["parameters"] for t in TOOLS if t["function"]["name"] == nome)
        validar(argumentos, esquema)
        resultado = funcao(**argumentos)
        return json.dumps(resultado, ensure_ascii=False) if isinstance(resultado, (dict, list)) else str(resultado)
    except Exception as exc:
        return f"❌ {nome}: {exc}"
