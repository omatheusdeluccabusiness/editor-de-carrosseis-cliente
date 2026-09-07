# ANB Style

Template editorial 1080 × 1350, com dez slides independentes. A referência visual é traduzida em composições fixas, sem reutilizar marca, fotografias ou conteúdo da referência.

## Composições

- Capa: foto integral, título de impacto e subtítulo.
- Editorial: texto e faixa de foto na parte inferior.
- Faixa central: texto, fotografia e conclusão em zonas separadas.
- Coluna lateral: texto à esquerda e fotografia à direita.
- Manifesto: composição escura e centralizada.
- Texto: página marfim sem fotografia, para conteúdo mais extenso.

O editor mede o texto e ajusta a fonte dentro de limites de legibilidade. Se o conteúdo exceder a área disponível, deve ser reduzido ou transferido para outro slide antes de exportar. A exportação utiliza o mesmo renderizador Canvas da prévia.

## Edição e continuidade

Os textos são editados diretamente sobre o slide: clique no título, corpo, conclusão ou assinatura e escreva. O painel lateral fica reservado aos ajustes de layout, formatação, foto e Vortex.

O carrossel é salvo automaticamente no próprio navegador, incluindo textos, fotos, layout e ajustes. Recarregar a página restaura a criação; somente o botão **Reiniciar carrossel**, após confirmação, apaga esse estado. “Salvar projeto” continua disponível para baixar uma cópia JSON portátil.

As imagens são processadas no navegador. Não há envio para Supabase nem armazenamento remoto.

## Vortex

No painel Vortex, ative “Borrado radial + grão” para a fotografia do slide. O algoritmo é o mesmo do Stories com fundo, com força, área central preservada e posição do centro ajustáveis. O texto não recebe desfoque. As configurações acompanham o projeto JSON e a exportação PNG/ZIP. Projetos antigos abrem com o efeito desligado. É necessário suporte a WebGL; se indisponível, a exportação avisa para desativar o efeito.

## Tipografia

Títulos usam Anton, distribuída pelo Google Fonts sob SIL Open Font License; licença incluída em `assets/fonts/Anton-OFL.txt`. Serifada usa a Advercase já presente no editor.

Fonte Anton: https://github.com/google/fonts/tree/main/ofl/anton
