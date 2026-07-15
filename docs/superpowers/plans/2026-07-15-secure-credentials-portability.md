# Secure Credentials Portability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Versionar um cofre criptografado que restaura automaticamente as credenciais locais de Telegram e Meta em um clone novo.

**Architecture:** `scripts/credenciais.py` concentra criptografia, selagem, restauração e CLI. O ciphertext fica em `secrets/credentials.enc.json`; a chave e os arquivos restaurados ficam fora do Git. `start.sh` tenta restauração não interativa quando uma chave local já existe, enquanto `configurar-credenciais.sh` cobre o primeiro uso.

**Tech Stack:** Python 3.10+, `cryptography` AESGCM, Scrypt, unittest, Bash.

## Global Constraints

- Nunca versionar Telegram Bot Token, Meta App Secret ou access token em texto puro.
- Usar AES-256-GCM com Scrypt, salt e nonce aleatórios.
- Chave local em `~/.carrossel-editor-recovery-key`, modo `0600` em POSIX.
- Chave incorreta não pode alterar `.env` nem `~/.matheusao-telegram.json`.
- O projeto não pode depender de `claude-instagram` depois da selagem inicial.
- Preservar `http://localhost:8777` e os comandos atuais.

---

### Task 1: Primitivas criptográficas e envelope

**Files:**
- Create: `scripts/credenciais.py`
- Create: `tests/test_credentials.py`
- Modify: `requirements.txt`
- Modify: `tests/test_packaging.py`

**Interfaces:**
- Produces: `encrypt_payload(payload: dict, recovery_key: str) -> dict`
- Produces: `decrypt_payload(envelope: dict, recovery_key: str) -> dict`
- Produces: `generate_recovery_key() -> str`

- [ ] **Step 1: Escrever testes de round trip, chave incorreta e ausência de plaintext**

```python
payload = {"telegram": {"botToken": "bot-secret", "chatId": "123"}}
envelope = encrypt_payload(payload, "recovery-key")
self.assertEqual(decrypt_payload(envelope, "recovery-key"), payload)
self.assertNotIn("bot-secret", json.dumps(envelope))
with self.assertRaises(CredentialsError):
    decrypt_payload(envelope, "wrong-key")
```

- [ ] **Step 2: Rodar o teste e confirmar falha por módulo ausente**

Run: `python3 -m unittest tests.test_credentials -v`
Expected: FAIL com `ModuleNotFoundError: scripts.credenciais`.

- [ ] **Step 3: Adicionar `cryptography>=42,<47` e implementar AESGCM + Scrypt**

```python
def _derive_key(recovery_key: str, salt: bytes) -> bytes:
    return Scrypt(salt=salt, length=32, n=2**14, r=8, p=1).derive(
        recovery_key.encode("utf-8")
    )
```

O envelope deve conter `version`, `kdf`, `salt`, `nonce` e `ciphertext`, todos os bytes em base64 URL-safe.

- [ ] **Step 4: Rodar testes de credenciais e empacotamento**

Run: `python3 -m unittest tests.test_credentials tests.test_packaging -v`
Expected: PASS.

### Task 2: Selagem, restauração e inicialização

**Files:**
- Modify: `scripts/credenciais.py`
- Modify: `tests/test_credentials.py`
- Create: `configurar-credenciais.sh`
- Modify: `start.sh`
- Modify: `.gitignore`
- Modify: `README.md`

**Interfaces:**
- Consumes: `encrypt_payload`, `decrypt_payload`, `generate_recovery_key`
- Produces: `seal_credentials(telegram_path, meta_env_path, vault_path, key_path) -> None`
- Produces: `restore_credentials(vault_path, key_path, project_env_path, telegram_path) -> None`
- Produces CLI subcommands `seal`, `restore`, `status`

- [ ] **Step 1: Escrever testes com diretórios temporários**

```python
seal_credentials(telegram_source, meta_source, vault, key_file)
restore_credentials(vault, key_file, restored_env, restored_telegram)
self.assertIn("INSTAGRAM_ACCESS_TOKEN=", restored_env.read_text())
self.assertEqual(json.loads(restored_telegram.read_text())["chatId"], "123")
self.assertEqual(stat.S_IMODE(key_file.stat().st_mode), 0o600)
```

O teste de chave incorreta deve criar sentinelas nos destinos, falhar e verificar que elas não foram alteradas.

- [ ] **Step 2: Rodar teste e confirmar falha das funções ausentes**

Run: `python3 -m unittest tests.test_credentials -v`
Expected: FAIL por imports ausentes.

- [ ] **Step 3: Implementar parsing sem logs de valores e escrita atômica**

```python
def _atomic_write(path: Path, content: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temp_path = Path(handle.name)
    os.chmod(temp_path, mode)
    temp_path.replace(path)
```

- [ ] **Step 4: Criar bootstrap e integrar ao start**

`configurar-credenciais.sh` executa `python3 scripts/credenciais.py restore`. `start.sh` executa `restore --if-needed --non-interactive` antes de iniciar o supervisor; ausência de chave não bloqueia o editor local.

- [ ] **Step 5: Documentar primeiro uso no outro computador**

Documentar clonagem, instalação, cópia separada da chave de recuperação e `./configurar-credenciais.sh`, sem incluir a chave no README.

- [ ] **Step 6: Rodar testes e shell syntax**

Run: `python3 -m unittest tests.test_credentials -v && bash -n start.sh configurar-credenciais.sh`
Expected: PASS.

### Task 3: Criar o cofre real e provar portabilidade

**Files:**
- Create: `secrets/credentials.enc.json`
- Local only: `~/.carrossel-editor-recovery-key`

**Interfaces:**
- Consumes CLI `seal` e `restore`
- Produces ciphertext versionado e chave local não versionada

- [ ] **Step 1: Selar fontes locais existentes**

Run: `python3 scripts/credenciais.py seal --telegram ~/.matheusao-telegram.json --meta-env /Users/matheusdelucca/claude-instagram/.env`
Expected: informa somente caminhos criados, nunca valores.

- [ ] **Step 2: Auditar ciphertext e staged files**

Run: `git grep -I -l -E 'gh[pousr]_|sk-|INSTAGRAM_ACCESS_TOKEN=.+' -- .`
Expected: nenhum segredo real; ocorrências em código/testes devem ser apenas placeholders controlados.

- [ ] **Step 3: Simular clone sem configuração**

Copiar arquivos rastreados para um diretório temporário, instalar dependências, copiar somente a chave local separadamente e rodar `restore` apontando destinos temporários.

- [ ] **Step 4: Validar formatos restaurados sem imprimir valores**

Verificar apenas nomes de variáveis, chaves JSON e presença de valores não vazios.

### Task 4: Verificação e publicação

**Files:**
- Modify: somente arquivos desta feature

**Interfaces:**
- Consumes todos os artefatos anteriores
- Produces branch publicada e pronta para integração

- [ ] **Step 1: Rodar verificação completa**

Run: `python3 -m unittest discover -s tests -v`
Expected: todos os testes PASS.

Run: `python3 -m py_compile scripts/*.py`
Expected: exit 0.

Run: `curl -sS -o /dev/null -w '%{http_code}' http://localhost:8777/validacao-editor-final.html`
Expected: `200`.

- [ ] **Step 2: Auditar diff e secrets antes do commit**

Run: `git diff --check && git status --short && git diff --stat`
Expected: somente arquivos planejados.

- [ ] **Step 3: Commitar e publicar a branch**

```bash
git add .gitignore README.md requirements.txt start.sh configurar-credenciais.sh \
  scripts/credenciais.py tests/test_credentials.py tests/test_packaging.py \
  secrets/credentials.enc.json docs/superpowers/plans/2026-07-15-secure-credentials-portability.md
git commit -m "Adiciona cofre portatil de credenciais"
git push -u origin agent/secure-credentials-portability
```

- [ ] **Step 4: Confirmar remoto e privacidade**

Run: `gh repo view --json visibility,defaultBranchRef,url`
Expected: `PRIVATE`, branch remota disponível e nenhum arquivo local de chave rastreado.
