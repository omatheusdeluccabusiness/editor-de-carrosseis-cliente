# Native Studio — revisão visual da página do editor

## Objetivo

Substituir o shell visual atual dos editores Tweet e Stories por uma interface de criação com acabamento próximo a um aplicativo nativo da Apple. O trabalho cobre apenas a página que organiza o editor: cabeçalho, navegação dos slides, área de trabalho e inspector. O conteúdo e os controles internos dos slides permanecem funcionais.

## Direção

O produto é uma ferramenta local de produção de carrosséis usada por uma única pessoa. A página deve desaparecer ao redor do trabalho: o slide é o protagonista, as ações frequentes ficam próximas e as configurações secundárias permanecem acessíveis sem competir pela atenção.

A referência não é um dashboard SaaS. É um aplicativo criativo de desktop: compacto, preciso, silencioso e familiar.

## Sistema visual

### Tipografia

- Interface: `-apple-system`, `BlinkMacSystemFont`, `"SF Pro Text"`, `"SF Pro Display"`, `Inter`, `sans-serif`.
- Títulos usam o mesmo sistema com peso 600 e espaçamento negativo discreto.
- Metadados usam algarismos tabulares da própria família, sem fonte monoespaçada decorativa.
- Nenhum rótulo funcional usa caixa alta ou letter-spacing artificial.

### Cores

- Canvas da aplicação: `#F2F2F4`.
- Superfície principal: `#FFFFFF`.
- Superfície secundária: `#F7F7F8`.
- Texto principal: `#1D1D1F`.
- Texto secundário: `#6E6E73`.
- Divisória: `#D2D2D7` com transparência contextual.
- Ação e seleção: `#007AFF`.
- Destrutivo: `#FF3B30`.

Não há amarelo de destaque. Azul aparece apenas em ações primárias, foco e seleção.

### Forma e profundidade

- Raios de 8, 10 e 12 px, usados de acordo com a escala do componente.
- Divisórias de 1 px e sombras muito suaves, nunca contornos escuros.
- Controles têm altura entre 30 e 36 px no desktop.
- Estados ativos são indicados por fundo azul suave, texto azul e, quando necessário, uma barra de seleção de 3 px.

## Layout

### Desktop

```text
┌─────────────────────────────────────────────────────────────┐
│ título / status                         exportar  publicar  │
├──────────────┬────────────────────────────┬─────────────────┤
│ Slides       │ Área de trabalho           │ Inspector       │
│ miniaturas   │                            │ Documento       │
│ e ações      │        slide ativo         │ Legenda         │
│              │                            │ Entrega         │
└──────────────┴────────────────────────────┴─────────────────┘
```

- Cabeçalho de 64 px, fixo e branco quase opaco. O blur foi descartado porque interfere com a composição das camadas transformadas do editor Stories.
- Sidebar esquerda de aproximadamente 220 px.
- Inspector direito de aproximadamente 300 px.
- Área central sobre fundo cinza-claro, com o slide isolado visualmente.
- Sidebars usam superfícies contínuas. Não parecem cartões flutuantes independentes.

### Tablet

- Roteiro vira uma faixa horizontal acima do canvas.
- Inspector permanece lateral enquanto houver largura útil.

### Mobile

- Cabeçalho ocupa duas linhas compactas.
- Slides aparecem em faixa horizontal rolável.
- Canvas usa toda a largura disponível sem overflow.
- Inspector entra abaixo do editor em seções simples.

## Componentes

### Cabeçalho

- Título em 17–20 px e metadados em 12 px.
- Status de salvamento discreto ao lado do título.
- `Exportar PNGs` é secundário; `Publicar` é primário azul.
- Sem eyebrow, logotipo inventado ou caixa alta decorativa.

### Navegação dos slides

- Cabeçalho simples: `Slides` e contagem.
- Cada item contém número, papel do slide e indicação de seleção.
- Seleção usa azul suave e uma barra azul à esquerda.
- Adicionar fica no rodapé da sidebar; excluir é uma ação secundária destrutiva.

### Área de trabalho

- Fundo `#F2F2F4`, sem borda de cartão ao redor do canvas.
- Instruções curtas aparecem numa barra contextual discreta.
- Controles específicos do slide ficam próximos ao canvas, em uma toolbar branca compacta.

### Inspector

- Superfície branca contínua com seções separadas por divisórias.
- Títulos em sentence case, 13 px, peso 600.
- Campos e segmented controls seguem o mesmo sistema de alturas e raios.
- Telegram e manutenção ficam abaixo das propriedades do documento.

## Interação e acessibilidade

- Hover altera apenas fundo ou opacidade; nenhum componente salta.
- Foco por teclado usa anel azul de 3 px com transparência.
- Transições entre 120 e 180 ms.
- `prefers-reduced-motion` remove transições e rolagem suave.
- Contraste preserva legibilidade em todos os estados.
- IDs, handlers e fluxos existentes de edição, publicação, Telegram e exportação permanecem intactos.

## Assinatura visual

O elemento memorável é o enquadramento do slide como objeto de trabalho: canvas limpo sobre uma mesa cinza-clara, com sidebars contínuas e discretas. A personalidade vem da precisão e da ausência de ruído, não de decoração.

## Critérios de aceite

1. Tweet e Stories usam a pilha tipográfica próxima de SF Pro e não carregam Barlow Condensed, Source Sans 3 ou IBM Plex Mono no shell.
2. A interface não usa amarelo como ação ou destaque.
3. Cabeçalho, sidebar, canvas e inspector têm hierarquia visual equivalente a um aplicativo nativo.
4. Os controles existentes continuam funcionando com os mesmos IDs e handlers.
5. Não existe overflow horizontal em 1440 px, 1024 px ou 390 px.
6. O canvas Tweet continua escalando corretamente no mobile.
7. A toolbar de Stories permanece oculta sem seleção e aparece ao selecionar um bloco.
8. Testes automatizados, compilação Python, regeneração dos HTMLs e respostas HTTP locais passam antes da entrega.

## Fora do escopo

- Redesenhar o conteúdo visual de cada slide.
- Alterar geração de imagens, publicação, Telegram ou persistência.
- Introduzir framework CSS ou dependência de frontend.
