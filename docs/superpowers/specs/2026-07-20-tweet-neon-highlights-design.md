# Realce neon no editor Tweet

## Objetivo

Adicionar ao editor `Tweet` uma ferramenta de marca-texto para palavras e
frases. O realce deve ter aparência de tinta fluorescente aplicada sobre o
papel, continuar editável, adaptar-se automaticamente aos temas claro e escuro
e aparecer no PNG exatamente como aparece na pré-visualização.

Esta primeira versão não altera `Stories` nem `Ostentação`.

## Experiência de uso

1. O usuário seleciona uma palavra ou frase dentro do texto de um slide Tweet.
2. Uma paleta contextual compacta aparece próxima à seleção.
3. A paleta oferece amarelo, rosa, verde e azul, além da ação `Remover realce`.
4. A escolha é aplicada sem perder a seleção e fica disponível para desfazer
   pelo fluxo nativo de edição.
5. Ao trocar o tema do documento, todos os realces assumem imediatamente a
   variante visual correspondente ao novo tema.

A paleta só aparece quando a seleção:

- não está vazia;
- pertence integralmente a um único `.tweet-render .body`;
- não atravessa dois slides ou elementos fora do texto editável.

Um clique fora da seleção, `Escape`, perda de foco ou seleção inválida fecha a
paleta. Os botões usam nome acessível, foco visível e estado identificável sem
depender exclusivamente da cor.

## Direção visual

O marca-texto é o único gesto expressivo novo. A interface ao redor continua
silenciosa e próxima de um aplicativo nativo.

O efeito não é um retângulo chapado. Cada trecho recebe uma faixa que começa
abaixo do topo das letras, ultrapassa discretamente as laterais e termina antes
da base da linha. As extremidades têm variação geométrica pequena e
determinística, suficiente para sugerir uma passada de marcador sem produzir
ruído ou desalinhamento entre renderizações.

### Cores semânticas

O conteúdo salva apenas um dos identificadores `yellow`, `pink`, `green` ou
`blue`. As cores efetivas pertencem ao tema:

| Cor | Tema claro | Tema escuro |
| --- | --- | --- |
| Amarelo | `rgba(255, 228, 94, 0.82)` | `rgba(172, 129, 0, 0.78)` |
| Rosa | `rgba(255, 122, 200, 0.76)` | `rgba(145, 35, 88, 0.76)` |
| Verde | `rgba(128, 226, 126, 0.76)` | `rgba(24, 108, 64, 0.78)` |
| Azul | `rgba(100, 216, 255, 0.76)` | `rgba(16, 94, 132, 0.80)` |

O texto mantém a cor natural do tema: escuro no tema claro e claro no tema
escuro. A paleta exibe a mesma família cromática, mas não grava valores RGB no
conteúdo.

## Representação e persistência

O estado persistido continua baseado no campo `slidesState[index].text`. O
realce usa uma extensão limitada do markdown existente:

```text
[hl=yellow]trecho realçado[/hl]
```

Os valores aceitos são somente `yellow`, `pink`, `green` e `blue`. A marcação
pode conter `**negrito**` e quebras de linha. A combinação é restaurada como
HTML sem aceitar atributos, tags ou cores arbitrárias.

No DOM editável, o formato canônico é:

```html
<mark data-highlight="yellow">trecho realçado</mark>
```

O conversor `markdownToHtml` escapa o texto antes de produzir as tags
permitidas. O conversor `htmlToMarkdown` passa a caminhar pela árvore do DOM
para preservar, de forma determinística, texto, quebras, negrito e realce. Tags
desconhecidas não são persistidas. Identificadores de cor desconhecidos são
tratados como texto comum, nunca como HTML executável.

Aplicar uma cor sobre uma seleção que já contém realces substitui os realces
intersectados pela nova cor, preservando o negrito. `Remover realce` retira
somente a marcação de cor da seleção e preserva texto, negrito e quebras.

## Componentes e responsabilidades

### Paleta contextual

- Mantém uma cópia segura do `Range` ativo enquanto o usuário aciona um botão.
- Posiciona-se acima da seleção e, quando não houver espaço, abaixo dela.
- Permanece dentro da viewport.
- Aplica ou remove uma cor e devolve o foco ao corpo editável.
- Atualiza `slidesState`, armazenamento local, status de salvamento e trilho
  pelos mesmos caminhos usados pela edição atual.

### Serialização de texto rico

- Converte markdown limitado em DOM seguro.
- Converte DOM editável no markdown canônico.
- Normaliza realces aninhados ou adjacentes da mesma cor.
- Preserva a combinação de negrito, realce e quebras de linha.

### Leitura das linhas do DOM

`getLineSegmentsFromDOM` passa a produzir segmentos com:

```text
{ text, bold, highlight }
```

`highlight` é `null` ou um dos quatro identificadores permitidos. Uma mudança
de peso ou de cor inicia um novo segmento. As quebras reais calculadas pelo
navegador continuam sendo a fonte de verdade para a exportação.

### Renderização no canvas

- Agrupa segmentos realçados contíguos na mesma linha.
- Desenha a faixa de marcador antes de desenhar os glifos.
- Usa a tabela cromática do tema ativo.
- Usa geometria determinística; exportar novamente produz o mesmo resultado.
- Mantém texto e largura idênticos ao DOM, inclusive com negrito.

## Temas

O tema não modifica o conteúdo persistido. `body.theme-dark` altera apenas os
tokens CSS e a tabela usada pelo canvas. Assim, trocar entre claro e escuro não
gera uma nova versão do texto nem exige regravar os slides.

Um realce escolhido no tema claro deve continuar semanticamente igual no tema
escuro e voltar à variante clara quando o tema for revertido.

## Tratamento de falhas e casos de borda

- Seleção vazia ou fora do corpo editável: nenhum comando é aplicado.
- Seleção atravessando slides: a paleta permanece oculta.
- Marcação incompleta no estado legado: os delimitadores são exibidos como
  texto seguro, sem apagar a copy.
- Cor desconhecida: o trecho é mantido sem realce.
- Conteúdo colado: HTML externo continua descartado; apenas texto simples e a
  sintaxe limitada já aceita pelo editor são interpretados.
- Realce atravessando uma quebra: cada linha recebe sua própria faixa visual.
- Realce combinado com negrito: ambos são preservados na edição e no PNG.
- Tema trocado com a paleta aberta: a paleta e a pré-visualização atualizam sem
  perder o estado semântico da seleção.

## Acessibilidade

- A paleta usa `role="toolbar"` e nome acessível.
- Cada cor possui `aria-label` textual.
- A ação de remoção usa ícone e texto acessível, não apenas uma amostra branca.
- `Escape` fecha a paleta e mantém o foco no texto.
- O foco por teclado segue o anel azul já usado pelo shell.
- `prefers-reduced-motion: reduce` elimina a transição de entrada da paleta.

## Estratégia de testes

1. Testes automatizados começam falhando e cobrem a presença da paleta, as
   quatro cores semânticas, a ação de remoção e os atributos acessíveis.
2. Testes verificam os dois mapas cromáticos e impedem valores de cor livres no
   estado persistido.
3. Testes verificam os conversores e os segmentos esperados para texto simples,
   negrito, realce, combinação e quebra de linha.
4. Testes verificam que o canvas desenha o marcador antes do texto e escolhe o
   mapa do tema ativo.
5. A suíte completa, a compilação Python e a sintaxe dos scripts shell são
   executadas após a implementação.
6. Um HTML Tweet é regenerado e validado em `localhost:8777`.
7. A verificação visual cobre seleção, aplicação das quatro cores, remoção,
   troca de tema, atualização da página e exportação PNG.

## Critérios de aceite

1. Somente o editor Tweet recebe a nova feature.
2. Selecionar texto abre uma paleta contextual com quatro cores e remoção.
3. O realce persiste após atualizar a página.
4. Negrito e realce coexistem sem perda de conteúdo.
5. Claro e escuro usam variantes próprias sem regravar o texto.
6. O PNG corresponde visualmente à pré-visualização.
7. Aplicação, substituição e remoção não alteram texto fora da seleção.
8. A paleta funciona por mouse e teclado e não sai da viewport.
9. Nenhuma nova dependência JavaScript é introduzida.
10. Testes, compilação, regeneração e rota local passam antes da entrega.

## Fora do escopo

- Marca-texto em `Stories` ou `Ostentação`.
- Cores personalizadas ou seletor RGB.
- Controle de opacidade, espessura ou inclinação pelo usuário.
- Sincronização automática de estado entre computadores.
- Alterações nos fluxos de Telegram, Meta ou publicação.
