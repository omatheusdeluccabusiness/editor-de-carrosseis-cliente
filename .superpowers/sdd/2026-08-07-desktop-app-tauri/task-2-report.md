# Task 2 — Sidecar Python empacotável

## Arquivos

- Criado `scripts/desktop_sidecar.py`: entrypoint do binário desktop. Exige
  `CARROSSEL_APP_DATA_DIR`, cria e usa `<app-data>/sessions`, importa o mesmo
  `CarrosselHandler` de `serve_carrossel` e o expõe exclusivamente em
  `127.0.0.1`. Não chama `carrossel_service`.
- Criado `scripts/build_sidecar.py`: build PyInstaller `--onefile` com nome
  `editor-carrosseis-sidecar` (`.exe` no Windows), destino obrigatório via
  `--target-dir` e dados `templates`, `assets` e
  `secrets/credentials.enc.json`.
- Alterado `requirements.txt`: adiciona `pyinstaller>=6,<7`.
- Alterado `scripts/serve_carrossel.py`: em binário PyInstaller resolve os
  recursos a partir de `sys._MEIPASS`; em source preserva o root do projeto.
  Isso permite que os templates empacotados sejam realmente servidos.
- Alterado `tests/test_desktop_runtime.py`: caracteriza os dois entrypoints.
- Alterado `.gitignore`: ignora o executável gerado quando o destino for o
  repositório.

## Decisões

- A configuração de ambiente acontece antes de importar `serve_carrossel`,
  pois o módulo captura os caminhos de runtime no import.
- O builder usa `--hidden-import serve_carrossel` para o import tardio do
  sidecar ser incluído pelo PyInstaller.
- Arquivos de trabalho e spec do PyInstaller ficam em diretório temporário;
  nenhum artefato de build foi deixado no worktree.

## Validações

1. Antes da implementação: a suíte falhou como esperado, com
   `FileNotFoundError` para `scripts/desktop_sidecar.py` e
   `scripts/build_sidecar.py`. O `.venv` não existia inicialmente no
   worktree; a primeira execução usou o ambiente equivalente da árvore pai.
2. Criado `.venv` isolado do worktree e instalado `requirements.txt`.
3. `./.venv/bin/python -m unittest tests.test_desktop_runtime -v`
   - PASS: 5 testes.
4. `./.venv/bin/python -m py_compile scripts/*.py`
   - PASS.
5. `./.venv/bin/python scripts/build_sidecar.py --target-dir /tmp/carrossel-sidecar-task2c`
   - PASS: criou `/tmp/carrossel-sidecar-task2c/editor-carrosseis-sidecar`
     (macOS arm64, cerca de 5.9 MB).
6. Smoke sem usar a porta principal:
   `CARROSSEL_APP_DATA_DIR=/tmp/carrossel-desktop-data-task2c CARROSSEL_EDITOR_PORT=18878 /tmp/carrossel-sidecar-task2c/editor-carrosseis-sidecar`
   - `GET /api/health` retornou `{"ok": true, "service": "editor-carrosseis"}`.
   - `GET /` retornou HTTP 200.

## Preocupações

- O artefato validado é macOS arm64. O sufixo `.exe` é selecionado para
  Windows, mas a compilação cruzada/assinatura Windows deve ocorrer na etapa
  de empacotamento correspondente.
- O sidecar usa a porta configurada por `CARROSSEL_EDITOR_PORT` (8777 por
  padrão); o ciclo de vida e a escolha de porta pelo Tauri ficam para as
  tarefas seguintes.

## Fix round 1

- `hub_sessions` não executa mais `sys.executable` nem tenta despachar
  `roteiro_to_instagram.py` como subprocesso. Foi adicionada a API
  `generate_editor_from_markdown(...)`, que seleciona o template, faz parse e
  grava o HTML da sessão no mesmo processo. O CLI existente continua usando
  seu fluxo atual.
- O builder agora inclui somente `templates` e `assets`. O arquivo
  `credentials.enc.json` não é adicionado como dado PyInstaller; as
  credenciais ficam exclusivamente sob `CARROSSEL_APP_DATA_DIR`.
- `template_catalog` também reconhece `sys._MEIPASS`, para que os templates
  internos do arquivo one-file possam ser lidos durante a geração da sessão.
- Adicionado `tests/test_desktop_sidecar_smoke.py`: ele constrói o binário,
  verifica que o cofre não aparece no executável, sobe uma instância isolada
  e cria de verdade sessões Tweet e Stories por `POST /api/sessoes`.

Validação da correção:

1. `./.venv/bin/python -m unittest tests.test_hub_sessions tests.test_hub_editor_mode tests.test_desktop_runtime -v`
   - PASS: 11 testes.
2. `./.venv/bin/python -m unittest tests.test_desktop_sidecar_smoke -v`
   - PASS: gera um sidecar PyInstaller macOS arm64 e cria as duas sessões no
     binário congelado.
