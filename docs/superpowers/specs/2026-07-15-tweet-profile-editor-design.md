# Perfil editável do Modelo Tweet

## Objetivo

Adicionar ao inspector do Modelo Tweet um espaço explícito para qualquer usuário alterar foto de perfil, nome e arroba. As alterações aparecem imediatamente em todos os slides e também no PNG exportado.

## Interface

A seção `Perfil` fica no topo do inspector, antes de `Documento`.

Ela contém:

- avatar circular de 48 px;
- botão `Trocar foto` associado a um input de arquivo `accept="image/*"`;
- campo `Nome`;
- campo `Arroba`, exibido com um prefixo visual `@`;
- texto curto informando que o perfil vale para todos os slides.

Os controles seguem o sistema visual nativo existente. A seção não usa modal e permanece acessível no fluxo normal do inspector em desktop e mobile.

## Estado e persistência

O estado do perfil é global para o navegador:

```js
{
  name: "Matheusão | OSNL",
  handle: "omatheusdelucca",
  avatar: "data:image/jpeg;base64,..."
}
```

- Chave de armazenamento: `tweet-editor-profile-v1`.
- Na ausência de dados salvos, o editor usa os valores atuais do template.
- O campo de arroba aceita texto com ou sem `@`; o estado interno armazena o valor sem `@`.
- Nome ou arroba vazios permanecem editáveis e são exibidos como string vazia, sem substituir silenciosamente o que o usuário digitou.
- Uma falha ao ler o `localStorage` restaura apenas o perfil padrão e não impede o editor de abrir.

## Foto de perfil

Ao selecionar uma imagem:

1. o navegador lê o arquivo local;
2. a imagem é centralizada e recortada em um quadrado;
3. o resultado é reduzido para 512×512 px;
4. o editor salva um JPEG com qualidade 0,88 em formato data URL;
5. todos os slides e o preview do inspector são atualizados.

Arquivos que não possam ser decodificados exibem uma mensagem no status existente e preservam o avatar anterior.

## Integração com o editor

- `profileState` é a única fonte de verdade para nome, arroba e avatar.
- `buildUI()` usa `profileState` ao construir o cabeçalho de cada slide.
- `drawTweet()` recebe os valores atuais para exportar o mesmo perfil visto no preview.
- Alterações nos campos atualizam o DOM já renderizado sem reconstruir ou perder o foco do campo.
- A troca de avatar atualiza o objeto `avatarImg` usado pelo canvas.
- O perfil é compartilhado por todos os slides, mas não altera caption, publicação, Telegram ou conteúdo textual.

## Acessibilidade

- Campos possuem `label` visível.
- O avatar possui descrição textual.
- O botão de foto é operável por teclado.
- O estado de foco segue o anel azul existente.

## Critérios de aceite

1. A seção `Perfil` aparece antes de `Documento` no inspector do Tweet.
2. Nome, arroba e foto podem ser alterados pela interface.
3. A alteração aparece em todos os slides sem recarregar a página.
4. `drawTweet()` recebe o perfil atual ao exportar PNG.
5. O perfil permanece após recarregar o navegador.
6. O arroba não duplica `@` quando o usuário digita o prefixo.
7. Fotos grandes são centralmente recortadas e reduzidas para 512×512 px.
8. O layout não cria overflow horizontal em desktop ou mobile.
9. Testes, compilação Python, regeneração e validação HTTP passam.

## Fora do escopo

- Conta de usuário ou sincronização em servidor.
- Perfis diferentes por slide.
- Alteração do selo de verificação.
- Mudanças no Modelo Stories.
