# Undo global dos editores

## Objetivo

Permitir que `Ctrl+Z` no Windows/Linux e `⌘Z` no macOS desfaçam todas as alterações locais e reversíveis feitas nos editores Tweet e Stories.

## Escopo

O histórico cobre:

- texto, negrito, realces e estilos;
- nome, arroba, avatar e legenda;
- imagens adicionadas, removidas e reposicionadas;
- tema, proporção, espaçamentos e transformações;
- adição, exclusão, ordem e restauração de slides ou blocos.

Downloads, publicações, envios ao Telegram e alterações de credenciais não entram no histórico porque são efeitos externos, não edições reversíveis do documento. O template legado Ostentação permanece fora desta evolução, seguindo a arquitetura atual da interface de produção.

## Arquitetura

Cada template mantém um controlador autocontido de undo. O controlador guarda snapshots semânticos do documento, limita o histórico a 50 estados e elimina estados consecutivos idênticos. A pilha também é espelhada em `sessionStorage`, permitindo desfazer operações que hoje recarregam a página, como adicionar ou excluir slides.

O snapshot do Tweet contém slides, perfil, tema, proporção e legenda. O snapshot de Stories contém o documento estruturado, tema e legenda. Imagens continuam referenciadas pelos mesmos data URLs já usados pelo editor.

As funções existentes de persistência registram a transição após cada mutação. Assim, digitação, sliders e comandos já conectados ao estado entram no histórico sem criar uma segunda fonte de verdade.

## Comportamento

- `Ctrl+Z` e `⌘Z` desfazem exatamente o último estado editorial.
- O atalho funciona mesmo com foco em texto, inputs, sliders ou no canvas.
- `Ctrl+Shift+Z`, `⌘Shift+Z` e redo ficam fora deste escopo.
- Quando a quantidade de slides muda, o estado é restaurado e a página recarrega para religar os controles; nas demais ações, a restauração ocorre no lugar.
- Quando não existe histórico, o atalho não interfere no navegador.
- O editor exibe uma confirmação discreta de que a ação foi desfeita.

## Resiliência

Falhas ou limites de `sessionStorage` não interrompem a edição. O controlador reduz snapshots antigos até conseguir persistir; o histórico em memória continua funcionando na sessão atual.

## Validação

Testes automatizados verificam o contrato nos dois templates, a captura dos principais grupos de mutação, a persistência entre recargas e a exclusão de efeitos externos. A auditoria final exercita no navegador ao menos texto, tema e uma operação estrutural, além dos testes completos e da validação em `localhost:8777`.
