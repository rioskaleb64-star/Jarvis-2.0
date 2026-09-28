(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const overlay = $('centralOverlay');
  let dados = null, secao = 'comandos', pedido = null, aviso = null, focoAnterior = null;
  const enviar = (nome, valor) => {
    if (!window.jarvisUI.enviarComando(nome, valor)) window.jarvisUI.adicionarLog('sistema', 'Sem conexão com o JARVIS.');
  };
  function fechar() { overlay.hidden = true; focoAnterior?.focus(); }
  function abrir() {
    focoAnterior = document.activeElement; overlay.hidden = false;
    enviar('obter_painel'); mudarSecao(secao);
  }
  function mudarSecao(nome) {
    secao = nome;
    document.querySelectorAll('[data-pagina]').forEach(e => { e.hidden = e.dataset.pagina !== nome; });
    document.querySelectorAll('[data-secao]').forEach(e => e.classList.toggle('ativo', e.dataset.secao === nome));
    if (nome === 'voz') enviar('listar_vozes');
    if (nome === 'comandos') $('buscaComandos').focus();
    else $('fecharCentral').focus();
  }
  function preencher(texto) { fechar(); window.jarvisUI.preencher(texto); }
  function botao(texto, aoClicar) { const b=document.createElement('button');b.textContent=texto;b.addEventListener('click',aoClicar);return b; }
  function vazio(el, texto) { if (!el.children.length) { const p=document.createElement('p');p.className='muted';p.textContent=texto;el.append(p); } }
  function item(texto, detalhe, acoes=[]) {
    const div=document.createElement('div');div.className='item-central';
    const conteudo=document.createElement('div');conteudo.className='texto-item';conteudo.textContent=texto;
    if(detalhe){const pequeno=document.createElement('small');pequeno.textContent=detalhe;conteudo.append(pequeno);}
    div.append(conteudo);
    if(acoes.length){const botoes=document.createElement('div');botoes.className='acoes';acoes.forEach(b=>botoes.append(b));div.append(botoes);}
    return div;
  }
  function comandos() {
    const lista=$('listaComandos');lista.replaceChildren();
    const busca=$('buscaComandos').value.toLocaleLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');
    (dados?.comandos || []).filter(c => `${c.grupo} ${c.texto}`.toLocaleLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').includes(busca)).forEach(c=>{
      const b=botao('',()=>preencher(c.texto));b.className='comando';const cat=document.createElement('small');cat.textContent=c.grupo;const t=document.createElement('span');t.textContent=c.texto;b.append(cat,t);lista.append(b);
    });
    vazio(lista,'Nenhum comando encontrado. Você também pode escrever um pedido livre ao JARVIS.');
  }
  function renderizar() {
    if(!dados) return;
    comandos();
    const tarefas=$('listaTarefas');tarefas.replaceChildren();
    (dados.tarefas||[]).forEach(t=>tarefas.append(item(t.titulo,`Tarefa #${t.id}`,[botao('Concluir',()=>enviar('comando_texto',`Concluir tarefa ${t.id}`))])));
    vazio(tarefas,'Nenhuma tarefa pendente.');
    const lembretes=$('listaLembretes');lembretes.replaceChildren();
    (dados.lembretes||[]).forEach(r=>lembretes.append(item(r.texto,`#${r.id} · ${new Date(r.quando*1000).toLocaleString('pt-BR')} · ${r.estado==='disparado'?'aguardando conclusão':'agendado'}`,[botao('+5 min',()=>enviar('comando_texto',`Adiar lembrete ${r.id}`)),botao(r.estado==='disparado'?'Concluir':'Cancelar',()=>enviar('comando_texto',`${r.estado==='disparado'?'Concluir':'Cancelar'} lembrete ${r.id}`))])));
    vazio(lembretes,'Sem lembretes ativos.');
    const notas=$('listaNotas');notas.replaceChildren();
    (dados.notas||[]).forEach(n=>notas.append(item(n.titulo,n.resumo,[botao('Ler',()=>{fechar();enviar('comando_texto',`Ler nota ${n.id}`);})])));
    vazio(notas,'Suas anotações aparecerão aqui.');
    const memoria=$('listaMemoria');memoria.replaceChildren();
    Object.entries(dados.preferencias||{}).forEach(([chave,valor])=>memoria.append(item(chave,valor,[botao('Esquecer',()=>enviar('comando_texto',`Esqueça ${chave}`))])));
    vazio(memoria,'Nenhuma preferência memorizada.');
    const metricas=$('metricas');metricas.replaceChildren();const s=dados.sistema||{};
    [[`${s.cpu??'—'}%`,'CPU'],[`${s.ram??'—'}%`,'RAM em uso'],[`${s.disco_livre_gb??'—'} GB`,'Livres no disco do sistema'],[s.bateria==null?'Na tomada / sem bateria':`${s.bateria}%`,'Bateria']].forEach(([valor,nome])=>{const d=document.createElement('div');d.className='metrica';const v=document.createElement('strong');v.textContent=valor;const n=document.createElement('span');n.textContent=nome;d.append(v,n);metricas.append(d);});
    const integ=$('listaIntegracoes');integ.replaceChildren();
    (dados.integracoes||[]).forEach(i=>{const linha=item(i.nome,i.detalhe);const sinal=document.createElement('span');sinal.className='sinal'+(i.ok?'':' ausente');sinal.textContent=i.ok?'Disponível':'Não configurado';linha.append(sinal);integ.append(linha);});
    $('totalFerramentas').textContent=`${dados.ferramentas} ferramentas registradas. Indicadores de pacotes/chaves não testam a disponibilidade dos serviços externos.`;
  }
  window.addEventListener('jarvis:mensagem',({detail:m})=>{
    if(m.tipo==='painel'){dados=m;renderizar();}
    if(m.tipo==='vozes'){$('seletorVoz').replaceChildren();(m.opcoes||[]).forEach(v=>{const o=document.createElement('option');o.value=v.id;o.textContent=v.nome;$('seletorVoz').append(o);});$('seletorVoz').value=m.selecionada;}
    if(m.tipo==='config'){if(m.voz_escolhida)$('seletorVoz').value=m.voz_escolhida;$('velocidadeVoz').value=m.velocidade||0;}
    if(m.tipo==='confirmacao'){pedido=m.ativo?m:null;$('confirmacaoCard').hidden=!pedido;if(pedido){$('confirmacaoMensagem').textContent=m.mensagem;$('confirmarSim').disabled=false;}}
    if(m.tipo==='lembrete'){aviso=m;$('textoLembrete').textContent=m.texto;$('avisoLembrete').hidden=false;}
  });
  $('btnCentral').addEventListener('click',abrir);$('fecharCentral').addEventListener('click',fechar);
  overlay.addEventListener('click',e=>{if(e.target===overlay)fechar();});
  $('btnMinimizar').addEventListener('click',()=>enviar('minimizar'));$('btnSair').addEventListener('click',()=>enviar('sair'));
  document.querySelectorAll('[data-secao]').forEach(b=>b.addEventListener('click',()=>mudarSecao(b.dataset.secao)));
  document.querySelectorAll('[data-preencher]').forEach(b=>b.addEventListener('click',()=>preencher(b.dataset.preencher)));
  document.querySelectorAll('[data-comando]').forEach(b=>b.addEventListener('click',()=>enviar('comando_texto',b.dataset.comando)));
  $('buscaComandos').addEventListener('input',comandos);
  $('seletorVoz').addEventListener('change',()=>enviar('selecionar_voz',$('seletorVoz').value));
  $('velocidadeVoz').addEventListener('change',()=>enviar('velocidade_voz',Number($('velocidadeVoz').value)));
  $('amostraVoz').addEventListener('click',()=>enviar('testar_voz'));$('pararVoz').addEventListener('click',()=>enviar('parar_voz'));$('atualizarVozes').addEventListener('click',()=>enviar('listar_vozes'));
  $('confirmarSim').addEventListener('click',()=>{if(pedido)enviar('confirmar',{resposta:'sim',id:pedido.id});});
  $('confirmarNao').addEventListener('click',()=>{if(pedido)enviar('confirmar',{resposta:'cancela',id:pedido.id});});
  $('adiarAviso').addEventListener('click',()=>{if(aviso)enviar('comando_texto',`Adiar lembrete ${aviso.id}`);$('avisoLembrete').hidden=true;});
  $('concluirAviso').addEventListener('click',()=>{if(aviso)enviar('comando_texto',`Concluir lembrete ${aviso.id}`);$('avisoLembrete').hidden=true;});
  document.addEventListener('keydown',e=>{
    if(e.ctrlKey&&e.key.toLowerCase()==='k'){e.preventDefault();e.stopPropagation();overlay.hidden?abrir():fechar();}
    if(!overlay.hidden&&e.key==='Escape'){e.preventDefault();e.stopPropagation();fechar();}
    if(!overlay.hidden&&e.key==='Tab'){
      const foco=[...$('central').querySelectorAll('button,input,select')].filter(n=>n.getClientRects().length&&!n.disabled);
      const primeiro=foco[0],ultimo=foco[foco.length-1];
      if(e.shiftKey&&document.activeElement===primeiro){e.preventDefault();ultimo.focus();}
      else if(!e.shiftKey&&document.activeElement===ultimo){e.preventDefault();primeiro.focus();}
    }
  },true);
  setInterval(()=>{
    $('relogioCentral').textContent=new Date().toLocaleString('pt-BR');
    if(pedido){const s=Math.max(0,Math.ceil(pedido.prazo-Date.now()/1000));$('confirmacaoTempo').textContent=`Expira em ${s}s`;$('confirmarSim').disabled=!s;}
  },500);
})();
