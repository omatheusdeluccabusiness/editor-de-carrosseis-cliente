# Texto padrão dos slides

## Objetivo

Todo slide vazio criado pelo Editor de Carrosséis deve exibir exatamente:

`adicione aqui a sua copy`

A alteração vale para os modelos Tweet e Stories, para slides adicionados manualmente e para os cinco rascunhos existentes em `content/rascunhos/`.

## Escopo

- Substituir o conteúdo padrão dos 10 slides de um novo carrossel Tweet.
- Substituir o conteúdo padrão dos 17 slides de um novo carrossel Stories.
- Usar o mesmo conteúdo ao acionar o botão `+ Slide` nos dois editores.
- Atualizar apenas o conteúdo da seção `## Roteiro` dos rascunhos existentes.
- Preservar títulos, frontmatter, captions e demais metadados.
- Regenerar os HTMLs temporários correspondentes em `/tmp/carrossel-editor`.

O template legado Ostentação não recebe novos rascunhos pelo comando `novo.sh` e não faz parte desta alteração.

## Comportamento do parser

O parser atualmente combina parágrafos curtos antes de distribuí-los entre os slides. Como a nova copy padrão é curta, ele deve reconhecer esse valor como placeholder e preservar cada ocorrência como um parágrafo independente. Roteiros reais continuam usando a regra atual de agrupamento.

Com isso, dez ocorrências produzem dez slides no Tweet e dezessete ocorrências produzem dezessete slides no Stories.

## Compatibilidade

O texto será gravado como conteúdo real e editável, não como `placeholder` visual do navegador. Portanto, continuará aparecendo na exportação PNG até ser substituído pelo usuário.

Nenhuma copy já personalizada deve ser alterada automaticamente no futuro. A migração dos cinco rascunhos existentes é uma atualização pontual solicitada pelo usuário.

## Validação

- Teste automatizado inicialmente falhando para o placeholder e para a contagem de slides.
- Teste do conteúdo gerado por `tweet_placeholder` e `stories_placeholder`.
- Teste de preservação das ocorrências curtas pelo fatiador.
- Verificação estática dos dois templates para o texto do botão `+ Slide`.
- `python3 -m py_compile scripts/*.py`.
- Regeneração de pelo menos um Tweet e um Stories sem abrir o navegador.
- Resposta HTTP `200` para os HTMLs regenerados em `localhost:8777`.
- Conferência de que cada HTML contém a nova copy e não contém as frases antigas.
