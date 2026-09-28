"""Ciclo limitado de ferramentas, sem repetir ações após falhas de rede."""
import json


def ciclo_ferramentas(msg, mensagens, continuar, executar, pendente, ferramentas, max_rodadas=4, max_acoes=10):
    resultados = []
    executadas = {}
    total = 0
    for rodada in range(max_rodadas + 1):
        chamadas = getattr(msg, "tool_calls", None) or []
        if not chamadas:
            return msg.content or "\n".join(resultados) or "O modelo não retornou uma resposta."
        if rodada == max_rodadas:
            return "\n".join(resultados) + "\nLimite de etapas atingido; peça o próximo passo para continuar."
        mensagens.append({"role": "assistant", "content": msg.content,
                          "tool_calls": [c.model_dump(exclude_none=True) for c in chamadas]})
        for chamada in chamadas:
            if pendente():
                # Para imediatamente. A pergunta deve chegar intacta e a tempo de confirmar.
                return "\n".join(resultados)
            nome = chamada.function.name
            try:
                bruto = chamada.function.arguments
                if len(bruto) > 24000:
                    raise ValueError("argumentos longos demais")
                argumentos = json.loads(bruto)
                if not isinstance(argumentos, dict):
                    raise ValueError("argumentos devem ser um objeto")
                assinatura = (nome, json.dumps(argumentos, sort_keys=True, ensure_ascii=False))
                leitura = nome.startswith(("ler_", "listar_", "diagnostico_", "pesquisar_", "achar_")) or nome in {"calcular", "data_e_hora"}
                if assinatura in executadas and not leitura:
                    resultado = "Ação já executada neste pedido; resultado anterior: " + executadas[assinatura]
                elif total >= max_acoes:
                    resultado = "Limite de ações atingido. Nenhuma nova ação foi executada."
                else:
                    resultado = str(executar(nome, argumentos))
                    executadas[assinatura] = resultado
                    total += 1
            except (ValueError, TypeError, AttributeError) as exc:
                resultado = f"❌ Argumentos inválidos em {nome}: {exc}"
            resultados.append(resultado)
            mensagens.append({"role": "tool", "tool_call_id": chamada.id, "content": resultado[:16000]})
            if pendente():
                return "\n".join(resultados)
        if total >= max_acoes:
            return "\n".join(resultados)
        try:
            msg = continuar(mensagens, ferramentas)
        except Exception:
            # Resultados já executados são devolvidos; nunca repetir a ação no fallback.
            return "\n".join(resultados) + "\nNão consegui formular a resposta final da IA; estes são os resultados reais."
    return "\n".join(resultados)
