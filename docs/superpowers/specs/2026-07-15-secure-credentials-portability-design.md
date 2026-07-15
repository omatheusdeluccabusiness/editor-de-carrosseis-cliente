# Credenciais portáteis e criptografadas

## Objetivo

Permitir que o editor seja clonado em outro computador e continue publicando
no Telegram e no Instagram sem versionar tokens em texto puro. No primeiro
uso do novo computador, o usuário informa uma única chave de recuperação. Os
usos seguintes funcionam com os comandos normais do projeto.

## Decisão

O repositório conterá `secrets/credentials.enc.json`, um envelope criptografado
e autenticado. A chave de recuperação não será versionada. Ela ficará em um
arquivo local com permissão restrita e deverá ser transferida separadamente
para o outro computador.

O primeiro cofre será criado a partir das configurações locais existentes:

- `~/.matheusao-telegram.json`, para `botToken` e `chatId`;
- `/Users/matheusdelucca/claude-instagram/.env`, somente como fonte inicial das
  variáveis da Meta e do Instagram.

Depois da criação do cofre, o editor não dependerá dessas pastas externas.

## Criptografia e armazenamento

- AES-256-GCM para confidencialidade e autenticação do payload.
- Scrypt com salt aleatório para derivar a chave criptográfica.
- Nonce aleatório por selagem.
- Envelope JSON versionado contendo apenas metadados, salt, nonce e ciphertext.
- Chave local em `~/.carrossel-editor-recovery-key`, modo `0600` em sistemas
  POSIX.
- Arquivos restaurados: `.env` no projeto e
  `~/.matheusao-telegram.json`, ambos fora do Git.

O payload incluirá Telegram Bot Token, Chat ID, Instagram Business ID, access
token, versão da API, Meta App ID, Meta App Secret e metadados de conta que já
existirem na fonte.

## Experiência de uso

`./configurar-credenciais.sh` restaura as credenciais. Se a chave local não
existir, o comando pede que o usuário cole a chave de recuperação uma vez e a
salva localmente. O `./start.sh` executa uma restauração silenciosa quando a
chave já estiver instalada e os arquivos locais estiverem ausentes.

No Windows ou em ambientes sem Bash, o equivalente será:

```text
python scripts/credenciais.py restore
```

## Falhas e segurança

- Chave incorreta encerra o comando sem alterar arquivos existentes.
- Escritas são atômicas para evitar configuração parcial.
- Nenhum token, chave, tamanho ou trecho de credencial aparece nos logs.
- O teste automatizado verifica ida e volta da criptografia, falha com chave
  incorreta, ausência de plaintext no cofre e cobertura das dependências.
- A auditoria antes do push verifica que `.env`, arquivos de chave e JSON local
  não foram adicionados ao Git.

## Critérios de conclusão

1. O cofre versionado é criado sem conter credenciais legíveis.
2. Um diretório temporário simula um clone novo e restaura as credenciais com a
   chave de recuperação.
3. Telegram e Meta ficam configurados no formato esperado pelo editor.
4. A suíte de testes, a compilação Python e um HTML em localhost passam.
5. A branch é publicada no GitHub sem qualquer segredo em texto puro.
