# Editor de Carrosseis

Editor visual local para criar e exportar carrosseis nos modelos `tweet`,
`stories` e `ostentacao`. O projeto e independente de outros workspaces e usa
Python no servidor local, com os editores implementados em HTML, CSS e JavaScript.

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
./novo.sh tweet
./novo.sh stories
./stop.sh
```

O projeto usa `http://localhost:8777` e escreve os HTMLs temporarios em `/tmp/carrossel-editor`.
Abrir a raiz do localhost redireciona para o editor HTML mais recente.

Os rascunhos ficam em `content/rascunhos/`.

## Sincronizar alteracoes

Antes de comecar a trabalhar em outro computador:

```bash
git pull --ff-only
```

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

Se precisar conferir a configuracao sem revelar valores:

```bash
python3 scripts/credenciais.py status
```

## Estrutura

- `templates/`: HTML dos editores tweet, stories e ostentacao.
- `scripts/`: gerador, servidor local, supervisor persistente e publisher.
- `assets/`: imagens compartilhadas do editor.
- `content/rascunhos/`: markdowns criados pelo `./novo.sh`.
- `tests/`: verificacoes automatizadas do gerador e da interface.
