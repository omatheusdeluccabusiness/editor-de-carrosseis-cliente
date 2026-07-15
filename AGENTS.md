# Editor de Carrosseis

Este projeto e a pasta isolada para trabalhar exclusivamente no editor local de carrosseis.

## Objetivo

Manter e evoluir apenas o editor visual dos modelos:

- `tweet`: editor estilo post do X, normalmente 10 slides.
- `stories`: editor vertical de stories, normalmente 17 slides.
- `ostentacao`: template legado ainda mantido como referencia.

Nao puxar regras editoriais do vault Matheusao Brain para este projeto, a menos que o usuario peca explicitamente. Aqui o foco e produto/ferramenta local, nao criacao de pecas.

## Comandos principais

```bash
./start.sh
./novo.sh tweet
./novo.sh stories
./stop.sh
```

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
- `templates/tweet_editor.html`: template tweet.
- `templates/stories_editor.html`: template stories.

## Regras de trabalho

- Trabalhe dentro desta pasta quando a tarefa for sobre o editor.
- Preserve a porta `8777` para este pacote isolado.
- Nao depender de `/Users/matheusdelucca/Documents/Cofre Matheusão/Matheusão Brain` para rodar.
- Nao depender de `/Users/matheusdelucca/claude-instagram` para rodar o editor.
- Antes de concluir alteracoes, rode `python3 -m py_compile scripts/*.py` e valide ao menos um HTML em `localhost:8777`.
