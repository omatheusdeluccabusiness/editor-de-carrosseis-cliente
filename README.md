# Editor de Carrosseis

HUB local para criar, editar e finalizar carrosseis nos modelos Tweet e Stories,
ambos com 10 slides. O projeto e independente de outros workspaces e usa Python
no servidor local, com os editores implementados em HTML, CSS e JavaScript.

## Aplicativo desktop: usar sem terminal

Este e o fluxo para quem quer usar o editor no **macOS** ou **Windows** sem
Git, Codex, navegador externo ou comandos no terminal.

1. Baixe o artefato da sua plataforma no canal privado de distribuicao: `.dmg`
   para macOS; `.msi` ou `.exe` para Windows.
2. Abra o arquivo baixado e conclua a instalacao. Se o build ainda nao estiver
   assinado, o sistema pode exibir um aviso de seguranca na primeira abertura.
   Confirme a origem do arquivo com quem o disponibilizou antes de continuar.
3. Abra **Editor de Carrosseis** pelo Launchpad/Spotlight no macOS ou pelo Menu
   Iniciar/atalho no Windows. O HUB abre dentro do aplicativo; nao e necessario
   acessar um endereco localhost ou iniciar um servidor.
4. Escolha Tweet ou Stories, edite normalmente e use **Exportar PNGs** para
   salvar os arquivos em uma pasta escolhida pelo sistema.

O envio ao Telegram e opcional: a exportacao de PNGs continua disponivel sem
Telegram configurado. Caso deseje enviar, abra a opcao de Telegram no app e
faca um envio de teste depois de restaurar as credenciais locais.

### Restaurar credenciais com seguranca

Para configurar Telegram e Instagram em um computador novo, receba o arquivo
criptografado `credentials.enc.json` por um canal seguro, separadamente do
instalador. No HUB, abra **Configurar integrações**, selecione esse arquivo e
insira a **chave de recuperacao** somente naquele formulário do aplicativo. O
app valida o cofre e a chave antes de gravar a configuracao privada local; se a
validacao falhar, a configuracao existente nao e alterada. O cofre e a chave
nao entram no instalador, no repositorio ou no carrossel.

Nem o aplicativo nem o suporte solicitarao por chat o Telegram Bot Token, Chat
ID, Meta App Secret, token do Instagram ou a chave de recuperacao. Nao envie
esses dados em mensagens, capturas de tela ou documentos. Se alguem pedir um
deles, interrompa o atendimento e confirme por um canal confiavel.

### Atualizar o aplicativo

Quando houver uma versao nova, baixe o novo artefato da mesma plataforma e
instale-o sobre a versao atual. A atualizacao substitui o aplicativo, mas as
credenciais permanecem no armazenamento privado local e nao devem ser
reenviadas. Se o app solicitar a chave de recuperacao apos a atualizacao, use-a
somente na tela de restauracao do proprio app.

## Desenvolver com Codex

Este fluxo e tecnico e separado do aplicativo instalado. Ele exige Git, Python
3.10 ou superior e acesso ao repositorio privado no GitHub.

```bash
gh repo clone omatheusdeluccabusiness/editor-de-carrosseis
cd editor-de-carrosseis
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
./configurar-credenciais.sh
./start.sh
```

Abra `http://localhost:8777`, escolha Tweet ou Stories, edite e finalize pelo
HUB. O arquivo `AGENTS.md` contem o contexto e as regras operacionais para
trabalhar pelo Codex. O HUB nao mantem historico: cada sessao existe apenas
durante o uso local.

### Configurar Telegram pelo Bloco de Notas

Para enviar os slides ao Telegram, nao e preciso editar JSON nem usar comandos
de configuracao. Inicie o editor uma vez com `./start.sh`. Na pasta do projeto
sera criado o arquivo **`CREDENCIAIS_TELEGRAM.txt`**. Abra esse arquivo no
Bloco de Notas (Windows) ou TextEdit (macOS), preencha os dois campos e salve:

```text
TOKEN BOT TELEGRAM:
cole_o_token_do_bot_aqui

CHAT ID TELEGRAM:
cole_o_chat_id_aqui
```

Recarregue o HUB e use **Configurar Telegram → Testar configuração**. O TXT
preenchido e ignorado pelo Git, nunca e publicado no GitHub e nao e servido ao
navegador. O arquivo `CREDENCIAIS_TELEGRAM_MODELO.txt` que aparece no
repositorio e apenas a referencia vazia do formato.

O fluxo tecnico a partir de Markdown continua disponivel:

```bash
./novo.sh tweet
./novo.sh stories
```

Esses comandos criam rascunhos em `content/rascunhos/` e geram o editor
correspondente. Os HTMLs temporarios ficam em `/tmp/carrossel-editor`.

Para verificar a configuracao sem revelar valores:

```bash
python3 scripts/credenciais.py status
```

O repositorio guarda somente um cofre criptografado. Credenciais ficam fora do
Git; o servidor local aceita apenas conexoes de `127.0.0.1` e as operacoes que
alteram estado exigem origem local e token efemero.

## Estrutura

- `templates/`: HUB e HTML dos editores Tweet e Stories.
- `scripts/`: gerador, servidor local, supervisor persistente e publisher.
- `assets/`: imagens compartilhadas do editor.
- `content/rascunhos/`: markdowns criados pelo `./novo.sh`.
- `tests/`: verificacoes automatizadas do gerador e da interface.
