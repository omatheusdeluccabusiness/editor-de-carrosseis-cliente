# Task 5 — Documentacao de instalacao e qualidade final

## Entrega

- O `README.md` separa os fluxos **Aplicativo desktop: usar sem terminal** e
  **Desenvolver com Codex**.
- O guia do app instalado cobre download do artefato correto, instalacao,
  primeira abertura, exportacao de PNGs, Telegram opcional e atualizacao pela
  instalacao da versao nova.
- A chave de recuperacao deve ser inserida somente quando a tela do app a
  solicitar. O guia proibe compartilhar a chave, Bot Token, Chat ID e
  credenciais Meta por chat, capturas ou documentos.
- O aviso de seguranca de builds nao assinados em macOS e Windows esta
  documentado sem orientar a burlar verificacoes do sistema.
- `tests/test_packaging.py` protege os termos essenciais do guia desktop.

## Verificacao

1. O novo teste falhou inicialmente, como esperado, porque o README ainda nao
   tinha a secao `Aplicativo desktop`.
2. `./.venv/bin/python -m unittest tests.test_packaging -v` passou apos a
   documentacao ser adicionada.
3. `python3 -m py_compile scripts/*.py && ./.venv/bin/python -m unittest
   discover -s tests -v && ./start.sh && curl -fsS
   http://127.0.0.1:8777/api/health && ./stop.sh` passou. A suite incluiu os
   testes de runtime, empacotamento e integracao do sidecar; o health check
   retornou com sucesso e o servidor foi encerrado pelo `stop.sh`.
4. `git diff --check` passou.

## Limites conhecidos

- Esta tarefa nao construiu, publicou, instalou ou assinou nenhum artefato
  desktop. A documentacao informa corretamente que builds nao assinados podem
  exibir aviso na primeira abertura.
- `desktop/src-tauri/gen/` ja estava como arquivo gerado nao rastreado no
  worktree e foi preservado fora deste commit.
