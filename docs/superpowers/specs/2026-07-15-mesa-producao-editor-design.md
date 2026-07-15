# Mesa de produção do Editor de Carrosséis

## Sujeito, usuário e tarefa

O produto é um editor local de carrosséis para um operador-criador que produz peças Tweet e Stories. A página tem uma única tarefa: levar uma peça do rascunho até a exportação ou publicação sem perder a posição na sequência.

O visual interno de cada slide não faz parte desta mudança. A alteração cobre somente o shell operacional ao redor do editor.

## Direção visual

A página assume a metáfora de uma mesa de produção: sequência à esquerda, peça em edição no centro e propriedades à direita. A assinatura é um trilho vertical que representa a ordem narrativa real `Capa → Slides → CTA`.

### Tokens

- Papel: `#F5F6F4`
- Tinta: `#121416`
- Trilho: `#25292D`
- Ouro de publicação: `#F2B705`
- Azul de ação: `#1877D2`
- Vermelho destrutivo: `#C43D3D`
- Display: Barlow Condensed
- Interface: Source Sans 3
- Dados: IBM Plex Mono

## Estrutura

### Cabeçalho fixo

- Identifica o documento e o tipo do template.
- Exibe estado de salvamento.
- Mantém apenas `Exportar PNGs` e `Publicar` como ações globais visíveis.
- Publicar usa ouro; exportar é secundário.

### Trilho de produção

- Lista todos os slides com índice de dois dígitos.
- Usa os rótulos `Capa`, `Slide` e `CTA` quando disponíveis.
- Destaca o slide ativo e permite navegar até ele.
- Agrupa `Adicionar slide` e `Excluir atual` abaixo da sequência.

### Área central

- Preserva o HTML, o tamanho e os controles internos de cada slide.
- Mostra uma instrução curta sobre edição, colagem e arraste.
- Não adiciona decoração ao redor do canvas além do espaçamento necessário.

### Inspetor

- Agrupa formato e tema em `Documento`.
- Move a caption para `Legenda`.
- Agrupa Telegram em `Entrega`.
- Move restauração e limpeza para `Manutenção`, dentro de um elemento recolhível.
- No Stories, mantém as ações de imagem do slide ativo no inspetor.

## Comportamento

- Clicar em um item do trilho rola suavemente até o slide e o ativa.
- Selecionar um slide atualiza o trilho.
- Adicionar ou excluir continua usando os IDs e handlers existentes.
- Tweet e Stories compartilham a mesma linguagem de shell, sem unificar a lógica interna dos editores.
- O shell permanece claro; os botões de tema continuam alterando somente o visual dos slides.

## Responsividade e acessibilidade

- Desktop amplo: trilho, editor e inspetor em três colunas.
- Tablet: trilho horizontal acima do editor; inspetor abaixo.
- Mobile: cabeçalho quebra em duas linhas, trilho horizontal rolável e coluna única.
- Todos os controles têm foco visível.
- Movimento suave é removido quando `prefers-reduced-motion: reduce` estiver ativo.
- Ações destrutivas usam texto e cor; nunca dependem apenas da cor.

## Fora do escopo

- Redesenho dos slides Tweet ou Stories.
- Alterações no template legado Ostentação.
- Mudanças nos fluxos de publicação, Telegram, exportação ou persistência.
- Novas dependências JavaScript.

## Validação

- Testes estáticos para estrutura, tokens, responsividade, acessibilidade e IDs únicos.
- Compilação de todos os scripts Python.
- Regeneração de um Tweet e um Stories.
- Verificação visual em viewport desktop e mobile.
- Respostas HTTP `200` em `localhost:8777`.
