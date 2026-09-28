# Expansão do JARVIS

**Nova central de recursos:** consulte [GUIA_JARVIS.md](GUIA_JARVIS.md) para notas, tarefas, lembretes, Pomodoro, memória, diagnóstico, leitura de páginas no Brave e seleção de voz. Na interface, abra **CENTRAL** ou use **Ctrl+K**. Para verificar a instalação, execute **diagnosticar.bat**.

## Modo texto

Abra `iniciar_texto.bat` para iniciar sem captura de microfone e sem resposta falada. Se o listener já estiver aberto, use **Abrir modo texto** no menu do ícone da bandeja. No HUD, o botão **MODO TEXTO** alterna entre os modos. O campo fica visível, Enter envia e as mensagens permanecem na tela. Confirmações também podem ser digitadas (`sim` ou `cancela`).

## Preparação

Use o mesmo Python que inicia `jarvis_listener.py` e instale as dependências opcionais:

```powershell
python -m pip install screen-brightness-control tavily-python pyperclip openwakeword piper-tts
```

As dependências originais do projeto (`psutil`, `pywin32`, `pyautogui`, `pycaw`, `openai`, `pyaudiowpatch`, etc.) continuam necessárias. Os novos recursos que dependem de pacote ou serviço ausente retornam uma mensagem de erro sem derrubar o assistente.

Para pesquisa falada, configure `TAVILY_API_KEY` no ambiente do processo. A tool `pesquisar_na_web` envia a pergunta à Tavily e repassa o conteúdo ao modelo. `pesquisar_google` continua abrindo o navegador.

Para busca de arquivos, instale e execute o [Everything](https://www.voidtools.com/). Coloque a DLL **64 bits** da [Everything SDK](https://www.voidtools.com/support/everything/sdk/) como `Everything64.dll` nesta pasta ou defina `EVERYTHING_SDK_DLL` com o caminho completo. As tools `achar_arquivo`, `abrir_arquivo_por_nome` e `abrir_pasta_por_nome` dependem do índice estar ativo. Quando há mais de um resultado plausível, a abertura pede um nome mais específico.

Para ativação local, instale `openwakeword` e baixe os modelos uma vez:

```powershell
python -c "import openwakeword.utils; openwakeword.utils.download_models(model_names=['hey_jarvis_v0.1'])"
```

Depois diga **“Hey Jarvis”** ou aperte **Ctrl+Alt+J**. Sem o modelo, o listener mantém o atalho e não envia áudio à nuvem. Para permitir temporariamente o reconhecimento antigo via Google, defina `JARVIS_CLOUD_WAKE_FALLBACK=1`.

Para resposta falada, escolha uma voz instalada do Windows em **Central → Voz**. Para usar Piper, instale `piper-tts`, baixe uma voz `pt_BR` e coloque o `.onnx` e o `.onnx.json` na pasta `vozes`, ou defina `PIPER_VOICE_MODEL` para o `.onnx`. O botão de voz no HUD liga ou desliga a saída. O modelo Piper é carregado na primeira resposta, em segundo plano.

Wi-Fi usa a interface chamada `Wi-Fi`; se ela tiver outro nome, ajuste a tool `definir_wifi`. Wi-Fi e Bluetooth podem exigir execução como administrador. Alterar o tema pode precisar que alguns aplicativos sejam reiniciados para refletir a mudança.

## Confirmações e digitação

`matar_processo` nunca encerra os processos da lista protegida e exige confirmação para qualquer outro processo. `desligar_pc` e `reiniciar_pc` também exigem confirmação. A resposta deve ser uma frase curta e exata, como `sim`, `envia` ou `cancela`, dentro de 12 segundos. O HUD aceita a mesma resposta por texto. As solicitações e ações confirmadas são registradas no log.

Para ditar em outro aplicativo, deixe a caixa de texto em foco ou peça ao Jarvis para focar a janela pelo título. `digitar_na_janela_ativa` cola o texto. Com `enviar=false`, deixa o texto para revisão; com `enviar=true`, solicita confirmação antes de apertar Enter. O envio só acontece se a mesma janela continuar em foco.

## Verificação

```powershell
python -m py_compile jarvis.py jarvis_listener.py ferramentas.py ferramentas_browser.py browser_bridge.py hud_bridge.py mic_util.py wake_util.py tts_util.py Jarvis_watchdog.py
python -m unittest discover -s tests
python tests/smoke_bridges.py
```

A extensão do Brave em `extensao_jarvis` usa a porta local **8766**; o HUD usa **8765**. Depois de alterar os arquivos da extensão, recarregue-a em `brave://extensions` e reinicie o JARVIS para carregar o código Python atualizado.
