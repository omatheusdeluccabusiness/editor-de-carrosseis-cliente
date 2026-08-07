# Tipografia global no Stories

## Objetivo

Permitir que quem edita um carrossel Stories escolha uma tipografia geral e
aplique essa decisão automaticamente a todos os slides, à pré-visualização e
à exportação PNG.

## Escopo

- Somente `templates/stories_editor.html`.
- Um controle segmentado na seção existente **Documento**: `Serifada` e
  `Sem serifa`.
- `Serifada` continua sendo o padrão e preserva PT Serif.
- `Sem serifa` usa SF Pro no macOS e uma pilha nativa equivalente no Windows
  (`Segoe UI`) e demais sistemas.
- A escolha é armazenada no documento, persiste ao recarregar e participa do
  Ctrl/Cmd+Z.
- A renderização Canvas usa a mesma família selecionada, preservando paridade
  entre a prévia e o PNG de 1080x1350.

## Fora de escopo

- Não alterar Tweet.
- Não oferecer tipografia por slide ou por bloco.
- Não alterar o painel flutuante de blocos.
- Não baixar fontes externas novas.

## Decisões de interface

O editor de Stories atende criadores que precisam trocar a personalidade de
uma peça inteira sem criar inconsistência entre slides. O seletor fica em
**Documento**, junto às decisões globais. Ele usa duas opções escritas por
extenso, mantendo a superfície visual limpa e evitando siglas no painel de
formatação.

## Critérios de aceite

1. Uma escolha muda todos os slides renderizados.
2. A fonte padrão é serifada.
3. A escolha persiste, é restaurada pelo undo e aparece na exportação.
4. O selector é acessível por teclado, possui rótulos claros e não cria
   overflow em desktop ou mobile.
