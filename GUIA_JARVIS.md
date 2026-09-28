# JARVIS — guia da expansão

## Começar

Abra **iniciar_texto.bat**. Na janela, clique em **CENTRAL** ou pressione **Ctrl+K**.
Se o listener já estiver aberto, prefira **Abrir modo texto** no menu do ícone da bandeja.
Use **iniciar_listener.bat** para ativação por voz. Não é necessário adicionar `py` ao PATH para usar os iniciadores quando o Python instalado já é encontrado por eles.

O campo de texto aceita várias linhas: **Enter** envia, **Shift+Enter** quebra a linha. **↑** no início do campo recupera comandos anteriores; **↓** volta ao rascunho. Os botões no canto superior direito minimizam ou encerram a janela.

## Comandos sem IA

| Capacidade | Exemplo |
| --- | --- |
| Nota | `Anote: revisar as ideias do projeto` |
| Buscar / ler nota | `Buscar nota projeto` / `Ler nota 1` |
| Tarefa | `Nova tarefa: organizar a pasta de estudos` |
| Ver / concluir / reabrir | `Minhas tarefas` / `Concluir tarefa 1` / `Reabrir tarefa 1` |
| Lembrete relativo | `Me lembre em 10 minutos de beber água` |
| Lembrete com horário | `Me lembre amanhã 09:00 de estudar` |
| Temporizador | `Timer 30 segundos` |
| Consultar agenda | `Meus lembretes` |
| Adiar / cancelar | `Adiar lembrete 1 por 5 minutos` / `Cancelar lembrete 1` |
| Pomodoro | `Iniciar pomodoro` / `Cancelar pomodoro` |
| Memória explícita | `Lembre que meu nome é Carlos` |
| Ver / esquecer memória | `Minhas preferências` / `Esqueça meu nome` |
| Conta local | `Calcule (250 * 3) / 2` |
| Relógio | `Que horas são?` |
| Diagnóstico do computador | `Diagnóstico do PC` / `Processos pesados` |
| Configuração das integrações | `Status do Jarvis` |
| Exportação | `Exportar agenda` |
| Ajuda | `Ajuda` |

Os comandos também podem ser falados com “Jarvis” antes. Pedidos livres e compostos usam a IA configurada. O Pomodoro padrão tem quatro períodos de 25 minutos e pausas de 5; os parâmetros podem ser personalizados por pedido à IA.

### Lembretes

Os avisos funcionam com a janela principal aberta, inclusive minimizada. O listener sozinho **não dispara** os lembretes e o computador não é despertado. Ao reabrir o JARVIS, os avisos que venceram enquanto ele estava fechado aparecem. Um aviso disparado permanece na agenda até ser concluído, adiado ou cancelado.

Horários sem data, como `09:00`, significam a próxima ocorrência no horário local do Windows. Também são aceitos `hoje 20:00`, `amanhã 09:00`, `30/09/2026 15:00` e datas ISO com fuso. O limite é de um ano à frente.

### Dados e memória

Notas, tarefas, lembretes, preferências e escolha de voz ficam em **dados/jarvis.db**, um banco SQLite local. Preferências só são guardadas por comandos explícitos; não guarde senhas. As preferências salvas são enviadas ao provedor de IA como contexto ao conversar com ele.

`Exportar agenda` cria um novo JSON em **exportacoes/** com notas, tarefas, lembretes e preferências. Não sobrescreve exportações anteriores. Para backup completo, feche o JARVIS e copie a pasta **dados** junto do projeto. A exportação não inclui chaves do ambiente nem o histórico de conversa.

## Brave

Recarregue a extensão em **brave://extensions** após esta atualização. Ela continua na pasta **extensao_jarvis**.

- `Minhas abas` mostra títulos e endereços.
- `Leia a página atual` devolve o texto visível, ou o trecho selecionado, até 12 mil caracteres.
- `Resuma a página atual` usa esse texto para produzir um resumo com a URL da fonte; exige IA.
- Por pedido à IA: abrir uma aba por URL, duplicar a aba ativa, silenciar/restaurar o áudio, trocar ou fechar uma aba pelo título.

Para permitir a leitura, clique no ícone JARVIS do Brave enquanto estiver na página. Isso libera temporariamente a aba. O botão **Permitir leitura neste site** salva uma permissão para aquele site. Ela pode ser removida no mesmo painel. Páginas internas (`brave://`, `chrome://`), alguns PDFs e páginas protegidas podem impedir a leitura. Campos de formulários são excluídos da coleta. Resumos enviam o texto ao provedor de IA configurado.

O HUD usa a porta **8765**, com um token novo por sessão. A extensão usa **8766** e aceita conexões de extensões. Se configurar `JARVIS_BROWSER_PORT` ou `JARVIS_BROWSER_TOKEN`, atualize também `BRIDGE_URL` ou `TOKEN` em `extensao_jarvis/background.js` e a porta no manifesto.

## Escolher a voz

Abra **Central → Voz**. Escolha uma voz e clique em **Ouvir amostra**. A escolha é salva.

- **Windows:** usa as vozes SAPI instaladas, sem download de modelos. A velocidade pode ser ajustada na Central.
- **Piper:** coloque um modelo `.onnx` e o respectivo `.onnx.json` em **vozes/**, ou configure `PIPER_VOICE_MODEL`. Clique em **Atualizar vozes**. Requer `piper-tts`.
- **Parar fala:** interrompe a reprodução e limpa respostas pendentes da fila.

No modo texto, respostas normais ficam silenciosas. A amostra toca somente quando solicitada. No modo voz, o botão **VOZ** liga/desliga as respostas faladas. Piper pode levar mais tempo no primeiro carregamento; a velocidade ajustável na Central se aplica às vozes Windows.

## Estabilidade e limites

O registro valida tipos, parâmetros obrigatórios e limites antes das ferramentas de IA agirem. O ciclo suporta até quatro rodadas e dez execuções por pedido, sem repetir ações idênticas após falha de rede. Uma confirmação interrompe a sequência imediatamente; os botões **Confirmar / Cancelar** expiram em 12 segundos.

O programa impede cópias duplicadas do componente principal e do listener. A varredura de aplicativos inicializa o COM na própria thread, corrigindo o erro `CoInitialize não foi chamado`. Uma falha na animação não impede o carregamento dos controles do HUD.

Os diagnósticos mostram instalação/configuração das integrações, sem revelar as chaves. Uma chave presente não garante que o serviço remoto esteja disponível. Everything, modelos de voz, APIs e permissões administrativas continuam sendo requisitos dos recursos correspondentes.

## Diagnóstico e testes

Execute **diagnosticar.bat** para verificar Python, dependências, sintaxe e portas, sem abrir áudio. Consulte **jarvis_log.txt**, **jarvis_crash.log** e **listener_log.txt** se necessário.

Dependências principais: `python -m pip install -r requirements.txt`. O arquivo `requirements-opcionais.txt` lista recursos adicionais; instale apenas os desejados. Compatibilidade de modelos e pacotes de áudio depende da versão do Python.

```powershell
python -m unittest discover -s tests -v
python tests/smoke_bridges.py
python tests/smoke_backend.py
node tests/test_browser.js
```

Os testes de integração usam portas livres e dados temporários. Não iniciam captura de microfone, resposta falada, chamadas de IA nem ações no computador.

Referências da integração: [activeTab](https://developer.chrome.com/docs/extensions/develop/concepts/activeTab), [permissões por site](https://developer.chrome.com/docs/extensions/reference/api/permissions), [síntese Windows SAPI](https://learn.microsoft.com/en-us/previous-versions/windows/desktop/ee125647(v=vs.85)).
