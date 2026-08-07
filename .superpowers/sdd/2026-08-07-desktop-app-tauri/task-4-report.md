# Task 4 — Bundles e verificações de release

## Entrega

- Adicionado o workflow manual `Desktop release bundles`, sem publicação de
  release, para os runners nativos `macos-latest` e `windows-latest`.
- Cada job instala Python, dependências Python e Rust; executa toda a suíte
  Python; gera o sidecar PyInstaller no runner; copia-o para
  `desktop/src-tauri/binaries` com o target triple do Rust; instala dependências
  Node e executa `npm run build`.
- O job macOS anexa somente `.dmg`; o Windows anexa somente `.msi` e `.exe`,
  todos como artefatos privados de `actions/upload-artifact@v4`.
- `desktop/package.json` agora fornece `npm run build` e
  `npm run prepare-sidecar`; o README documenta o acionamento e a verificação
  local.
- `.gitignore` cobre dependências, alvos Tauri, sidecars estagiados e saídas
  de build/distribuição.

## Verificação

- Primeiro, o novo teste de workflow falhou como esperado porque
  `.github/workflows/desktop-release.yml` ainda não existia.
- `./.venv/bin/python -m unittest tests.test_desktop_packaging -v` passou:
  5 testes.
- `./.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -q` passou.
- `python3 -m py_compile scripts/*.py`, `git diff --check` e a validação YAML
  do workflow passaram.
- `git check-ignore` confirmou os cinco caminhos de saída previstos.
- `http://localhost:8777/` retornou HTTP 200.

## Limite

Os instaladores não foram publicados nem o workflow manual foi disparado deste
worktree; a execução ocorrerá apenas quando alguém o acionar no GitHub.

## Fix round 1

- `desktop/src-tauri/icons/` agora contém o conjunto gerado pelo Tauri a partir
  de uma imagem quadrada, incluindo `icon.icns`, `icon.ico` e `icon.png`; o
  `tauri.conf.json` não referencia mais o avatar não quadrado.
- O workflow limita o token a `contents: read`, desativa
  `persist-credentials` no checkout e fixa checkout, setup-python, toolchain
  Rust e upload-artifact em SHAs completos. Não há referência a secrets,
  `GITHUB_TOKEN` ou publicação de release.
- O teste Python faz parse do YAML, verifica permissões, SHA pins, preparação
  do sidecar por target, globs de upload, ausência de segredos e os ícones
  quadrados. O workflow falha antes do upload se o `.dmg`, `.msi` ou `.exe`
  correspondente não existir.
- O build macOS foi executado com `CARGO_TARGET_DIR` limpo e sem sidecar
  previamente estagiado; produziu
  `Editor de Carrosseis_0.1.0_aarch64.dmg`. Os `.msi` e `.exe` são validados
  exclusivamente pelo job `windows-latest`, pois não há cross-build para esses
  instaladores.
- `python3 -m py_compile scripts/*.py` e a suíte Python completa passaram
  depois da correção.
