"""Comandos úteis sem IA. Padrões completos evitam disparos em conversas."""
import re
import json


CATALOGO = [
    ("Agenda", "Me lembre em 10 minutos de beber água"),
    ("Agenda", "Me lembre amanhã 09:00 de revisar o projeto"),
    ("Agenda", "Timer 5 minutos"),
    ("Agenda", "Meus lembretes"),
    ("Foco", "Iniciar pomodoro"),
    ("Foco", "Cancelar pomodoro"),
    ("Tarefas", "Nova tarefa: revisar o Jarvis"),
    ("Tarefas", "Minhas tarefas"),
    ("Tarefas", "Concluir tarefa 1"),
    ("Notas", "Anote: minha ideia para o projeto"),
    ("Notas", "Minhas notas"),
    ("Notas", "Buscar nota projeto"),
    ("Notas", "Ler nota 1"),
    ("Memória", "Lembre que meu nome é Carlos"),
    ("Memória", "Minhas preferências"),
    ("Memória", "Esqueça meu nome"),
    ("Utilidades", "Calcule (250 * 3) / 2"),
    ("Utilidades", "Que horas são?"),
    ("Sistema", "Diagnóstico do PC"),
    ("Sistema", "Status do Jarvis"),
    ("Sistema", "Processos pesados"),
    ("Brave", "Minhas abas"),
    ("Brave", "Leia a página atual"),
    ("Brave", "Resuma a página atual"),
    ("Backup", "Exportar agenda"),
]


def tentar_local(texto, executar):
    funcao = executar
    def executar(nome, argumentos):
        resultado = funcao(nome, argumentos)
        if not isinstance(resultado, str):
            return resultado
        try:
            dados = json.loads(resultado)
        except (ValueError, TypeError):
            return resultado
        if not isinstance(dados, dict) or "ok" not in dados:
            return resultado
        if not dados["ok"]:
            return "❌ " + dados.get("error", "A operação não foi concluída.")
        if "text" in dados:
            return f"{dados.get('title', 'Página atual')}\n{dados.get('url', '')}\n\n{dados['text'] or dados.get('note') or 'Nenhum texto legível.'}" + ("\n[Trecho limitado]" if dados.get("truncated") else "")
        if "tabs" in dados:
            return "\n".join(f"{'●' if aba.get('active') else '○'} {aba.get('title', '')}\n{aba.get('url', '')}" for aba in dados["tabs"]) or "Nenhuma aba aberta."
        if "tab" in dados:
            return f"{dados.get('message', dados['tab'].get('title', 'Aba atual'))}\n{dados['tab'].get('url', '')}"
        return dados.get("message", resultado)
    texto = texto.strip()
    simples = {
        r"(?:minhas |listar )?notas": ("listar_notas", {}),
        r"(?:minhas |listar )?tarefas": ("listar_tarefas", {}),
        r"(?:meus |listar )?lembretes|minha agenda": ("listar_lembretes", {}),
        r"(?:minhas |listar )?prefer[eê]ncias|minha mem[oó]ria": ("listar_preferencias", {}),
        r"(?:iniciar |inicie |come[cç]ar |comece )?pomodoro": ("iniciar_pomodoro", {}),
        r"cancela(?:r)? pomodoro": ("cancelar_pomodoro", {}),
        r"diagn[oó]stico (?:do )?(?:pc|computador)": ("diagnostico_pc", {}),
        r"status (?:do )?jarvis|diagn[oó]stico (?:do )?jarvis": ("diagnostico_jarvis", {}),
        r"processos pesados": ("processos_pesados", {}),
        r"(?:que |quais )?horas s[aã]o\??|hora atual|data de hoje": ("data_e_hora", {}),
        r"exporta(?:r)? agenda": ("exportar_agenda", {}),
        r"(?:minhas|listar) abas": ("listar_abas_browser", {}),
        r"(?:leia|ler) (?:a )?p[aá]gina atual": ("ler_pagina_browser", {}),
        r"resum[aei] (?:a )?p[aá]gina atual": ("resumir_pagina_atual", {}),
    }
    if re.fullmatch(r"/?ajuda|comandos|o que voc[eê] faz\??", texto, re.I):
        return "Comandos locais (também disponíveis na Central):\n" + "\n".join(ex for _, ex in CATALOGO)
    for padrao, (nome, args) in simples.items():
        if re.fullmatch(padrao, texto, re.I):
            return executar(nome, args)
    padrões = [
        (r"(?:anote|anota|salvar nota)\s*:\s*(.+)", lambda m: ("salvar_nota", {"titulo": m[1][:80], "texto": m[1]})),
        (r"(?:nova tarefa|adicionar tarefa|criar tarefa)\s*:\s*(.+)", lambda m: ("criar_tarefa", {"titulo": m[1]})),
        (r"(?:concluir|conclua) tarefa #?(\d+)", lambda m: ("concluir_tarefa", {"id": int(m[1])})),
        (r"reabrir tarefa #?(\d+)", lambda m: ("concluir_tarefa", {"id": int(m[1]), "concluida": False})),
        (r"(?:ler|leia) nota #?(\d+)", lambda m: ("ler_nota", {"id": int(m[1])})),
        (r"buscar nota (.+)", lambda m: ("listar_notas", {"busca": m[1]})),
        (r"(?:calcule|calcula|calcular)\s+(.+)", lambda m: ("calcular", {"expressao": m[1]})),
        (r"(?:lembre|lembra) que (.+?) [eé] (.+)", lambda m: ("lembrar_preferencia", {"chave": m[1], "valor": m[2]})),
        (r"esque[cç]a (.+)", lambda m: ("esquecer_preferencia", {"chave": m[1]})),
        (r"cancela(?:r)? lembrete #?(\d+)", lambda m: ("cancelar_lembrete", {"id": int(m[1])})),
        (r"concluir lembrete #?(\d+)", lambda m: ("concluir_lembrete", {"id": int(m[1])})),
        (r"adiar lembrete #?(\d+)(?: por (\d+) minutos?)?", lambda m: ("adiar_lembrete", {"id": int(m[1]), "minutos": int(m[2] or 5)})),
        (r"(?:me lembre|me lembra|lembrete) em (\d+(?:[.,]\d+)?) (segundos?|minutos?|horas?) (?:de |para )?(.+)",
         lambda m: ("criar_lembrete", {"texto": m[3], "em_minutos": float(m[1].replace(",", ".")) * (1/60 if m[2].lower().startswith("seg") else 60 if m[2].lower().startswith("hora") else 1)})),
        (r"(?:timer|temporizador|cron[oô]metro)(?: de)? (\d+(?:[.,]\d+)?) (segundos?|minutos?|horas?)",
         lambda m: ("criar_lembrete", {"texto": "Temporizador concluído", "em_minutos": float(m[1].replace(",", ".")) * (1/60 if m[2].lower().startswith("seg") else 60 if m[2].lower().startswith("hora") else 1)})),
        (r"(?:me lembre|me lembra|lembrete) ((?:(?:hoje|amanh[aã]) )?\d{2}:\d{2}|\d{2}/\d{2}/\d{4} \d{2}:\d{2}) (?:de |para )?(.+)",
         lambda m: ("criar_lembrete", {"texto": m[2], "quando": m[1]})),
    ]
    for padrao, montar in padrões:
        match = re.fullmatch(padrao, texto, re.I | re.S)
        if match:
            nome, argumentos = montar(match)
            return executar(nome, argumentos)
    return None
