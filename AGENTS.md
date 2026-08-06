# Editor de Carrosseis

Este projeto e a pasta isolada para trabalhar exclusivamente no editor local de carrosseis.

## Objetivo

Manter e evoluir apenas o HUB local e seus dois modelos visuais:

- `Tweet`: editor estilo post do X, com 10 slides.
- `Stories`: editor vertical, com 10 slides.

Nao puxar regras editoriais do vault Matheusao Brain para este projeto, a menos que o usuario peca explicitamente. Aqui o foco e produto/ferramenta local, nao criacao de pecas.

## Comandos principais

```bash
./start.sh
./stop.sh
```

Abra `http://localhost:8777` para usar o HUB: escolha Tweet ou Stories, edite e
exporte PNGs ou envie o resultado ao Telegram. O HUB não mantém histórico de
sessões.

`./novo.sh tweet` e `./novo.sh stories` continuam disponíveis como fluxo
técnico: criam um rascunho Markdown em `content/rascunhos/` e geram o editor
correspondente.

O servidor isolado roda em:

```text
http://localhost:8777
```

Os HTMLs temporarios ficam em:

```text
/tmp/carrossel-editor
```

Os rascunhos markdown ficam em:

```text
content/rascunhos/
```

## Arquivos importantes

- `scripts/novo_carrossel.py`: cria rascunhos novos e dispara o gerador.
- `scripts/roteiro_to_instagram.py`: parser markdown -> HTML do editor.
- `scripts/serve_carrossel.py`: servidor HTTP e endpoints locais.
- `scripts/carrossel_service.py`: supervisor persistente start/stop/status.
- `templates/hub.html`: tela inicial do HUB.
- `scripts/template_catalog.py`: catálogo dos templates disponíveis no HUB.
- `scripts/hub_sessions.py`: sessões efêmeras do HUB.
- `templates/tweet_editor.html`: template Tweet.
- `templates/stories_editor.html`: template Stories.

## Regras de trabalho

- Trabalhe dentro desta pasta quando a tarefa for sobre o editor.
- Preserve a porta `8777` para este pacote isolado.
- Nao depender de `/Users/matheusdelucca/Documents/Cofre Matheusão/Matheusão Brain` para rodar.
- Nao depender de `/Users/matheusdelucca/claude-instagram` para rodar o editor.
- Antes de concluir alteracoes, rode `python3 -m py_compile scripts/*.py` e valide ao menos um HTML em `localhost:8777`.
