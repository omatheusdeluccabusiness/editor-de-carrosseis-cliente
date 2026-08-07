# Editor de Carrosseis

HUB local para criar, editar e finalizar carrosseis nos modelos Tweet e Stories,
ambos com 10 slides. O projeto e independente de outros workspaces e usa Python
no servidor local, com os editores implementados em HTML, CSS e JavaScript.

## Instalar em outro computador

Requisitos: Git, Python 3.10 ou superior e acesso ao repositorio privado no
GitHub.

```bash
gh repo clone omatheusdeluccabusiness/editor-de-carrosseis
cd editor-de-carrosseis
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
./configurar-credenciais.sh
```

Na primeira configuracao, cole a chave de recuperacao fornecida separadamente.
Ela sera salva apenas nesse computador em
`~/.carrossel-editor-recovery-key`. Depois disso, `./start.sh` restaura
automaticamente as configuracoes locais caso elas estejam ausentes.

No Windows, use o equivalente:

```powershell
py scripts/credenciais.py restore
```

Para trabalhar pelo Codex, abra essa pasta como workspace. O arquivo
`AGENTS.md` contem o contexto e as regras operacionais do projeto.

## Executar

```bash
./start.sh
```

Abra `http://localhost:8777`, escolha Tweet ou Stories, edite e finalize pelo
HUB. A partir do editor, exporte PNGs ou envie o resultado ao Telegram. O HUB
nao mantem historico: cada sessao existe apenas durante o uso local.

O fluxo tecnico continua disponivel para quem trabalha a partir de Markdown:

```bash
./novo.sh tweet
./novo.sh stories
```

Esses comandos criam rascunhos em `content/rascunhos/` e geram o editor
correspondente. Os HTMLs temporarios ficam em `/tmp/carrossel-editor`.

## Instaladores desktop

O GitHub Actions gera instaladores nativos sob demanda, sem publicar uma
release externa. Na aba **Actions**, execute o workflow **Desktop release
bundles**: ele compila o sidecar nativamente em cada plataforma e disponibiliza
artefatos privados com o `.dmg` do macOS e os instaladores `.msi` e `.exe` do
Windows. O workflow nao usa nem imprime credenciais.

Cada instalador e verificado no runner nativo da sua plataforma: o `.dmg` no
macOS e os `.msi`/`.exe` no Windows. Nao ha build cruzado para os instaladores
Windows.

Para conferir o empacotamento local, a partir de `desktop/`:

```bash
npm ci
npm run prepare-sidecar
npm run build
```

## Sincronizar alteracoes

Antes de comecar a trabalhar em outro computador:

```bash
git pull --ff-only
```

Esse comando atualiza o produto sem substituir as credenciais locais, que ficam
fora do Git.

Depois de alterar e validar o projeto:

```bash
git add -A
git commit -m "Descreva a alteracao"
git push
```

## Credenciais e publicacao

O repositorio guarda somente um cofre criptografado. Telegram Bot Token, Chat
ID, Meta App Secret e token do Instagram nunca aparecem em texto puro no Git.
O comando de configuracao restaura `.env` no projeto e
`~/.matheusao-telegram.json` no computador local, ambos ignorados pelo Git.

As credenciais do Telegram permanecem somente no servidor local: o navegador
consulta apenas se a integracao esta configurada e envia os PNGs para um
endpoint local protegido. O servidor aceita conexoes apenas de
`127.0.0.1` e exige origem local e um token efemero nas operacoes que alteram
estado. Ao descartar uma criacao pelo HUB, o HTML temporario e o estado daquela
sessao sao removidos; arquivos criados pelo fluxo tecnico nao sao afetados.

Se precisar conferir a configuracao sem revelar valores:

```bash
python3 scripts/credenciais.py status
```

## Estrutura

- `templates/`: HUB e HTML dos editores Tweet e Stories.
- `scripts/`: gerador, servidor local, supervisor persistente e publisher.
- `assets/`: imagens compartilhadas do editor.
- `content/rascunhos/`: markdowns criados pelo `./novo.sh`.
- `tests/`: verificacoes automatizadas do gerador e da interface.
