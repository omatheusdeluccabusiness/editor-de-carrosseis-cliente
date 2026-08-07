# App desktop do Editor de Carrosseis

## Objetivo

Distribuir o Editor de Carrosseis como aplicativo instalavel para macOS e Windows. A pessoa abre o app, cria um carrossel, exporta PNGs e, quando as credenciais locais estiverem configuradas, envia ao Telegram sem terminal, navegador externo, clone de repositorio ou conhecimento tecnico.

Tweet e Stories continuam sendo os unicos templates oficiais. A versao desktop preserva integralmente o comportamento atual do HUB local, da edicao, do undo, das imagens, dos PNGs e do Telegram.

## Decisao

Usar **Tauri 2** como casca nativa e manter o servidor Python existente como processo local empacotado (sidecar).

```text
App instalado
  -> janela Tauri
  -> inicia sidecar Python em 127.0.0.1:8777
  -> espera health check
  -> carrega o HUB local dentro da propria janela
  -> editores Tweet e Stories usam os endpoints locais existentes
```

O HTML e o backend Python nao serao reescritos em Rust, React ou Electron. Essa e a alternativa de menor risco porque preserva o sistema que ja foi validado na producao.

## Alternativas descartadas

### Executavel Python que abre o navegador

E mais simples de empacotar, mas deixa o produto com aparencia de servidor local e depende do navegador padrao. Nao atende bem ao objetivo de app instalavel.

### Electron com backend novo em Node

Criaria instaladores facilmente, mas obrigaria migrar ou duplicar o servidor, o fluxo de credenciais e a entrega ao Telegram. O peso e o risco de regressao na ferramenta central nao se justificam.

## Experiencia da pessoa usuaria

1. Baixa e instala `Editor de Carrosseis`.
2. Abre o aplicativo pelo Launchpad, Spotlight, Menu Iniciar ou atalho.
3. O HUB aparece dentro de uma janela nativa, sem endereco localhost visivel.
4. Escolhe Modelo Tweet ou Modelo Stories e trabalha normalmente.
5. Exporta PNGs para uma pasta escolhida pelo sistema ou envia ao Telegram.
6. Fecha e reabre o app sem perder a configuracao de credenciais ja restaurada.

Nao havera login, conta, nuvem, historico de carrosseis, sincronizacao entre computadores ou mudanca no catalogo de templates.

## Componentes

### Casca Tauri

- Janela unica, com titulo `Editor de Carrosseis`.
- Navega apenas para o servidor loopback iniciado pelo proprio app.
- Aguarda `GET /` responder antes de exibir o editor.
- Ao fechar a janela, encerra o processo Python filho.
- Se a porta 8777 estiver indisponivel, mostra uma mensagem clara e nao abre uma janela em branco.

### Sidecar Python

- Binario produzido com PyInstaller para cada plataforma.
- Inclui `scripts/`, `templates/`, `assets/` e dependencias Python em um pacote local autocontido.
- Inicia somente em `127.0.0.1:8777`; nunca expoe o servidor na rede.
- Usa um diretorio de dados da aplicacao em vez de `/tmp` para sessoes e logs.
- Continua usando o mesmo contrato HTTP e os mesmos testes do servidor atual.

### Dados e credenciais locais

- O cofre criptografado versionado continua sem segredos em texto puro.
- A chave de recuperacao fica apenas no computador da pessoa.
- Telegram e Meta sao restaurados no armazenamento privado da aplicacao; nao entram no instalador, no repositorio ou no HTML.
- Primeiro uso sem chave exibira a mesma orientacao segura para restaurar as credenciais. PNG continua utilizavel mesmo sem Telegram configurado.

## Empacotamento e distribuicao

Cada plataforma deve compilar seu proprio artefato:

| Plataforma | Artefatos | Ambiente de build |
| --- | --- | --- |
| macOS | `.dmg` e `.app` | macOS arm64; universal quando houver suporte |
| Windows | `.msi` e `.exe` | Windows x64 |

O repositorio tera GitHub Actions para compilar cada plataforma em runners compativeis e publicar os arquivos como artefatos de release privada. Uma maquina macOS nao produz um instalador Windows confiavel de forma nativa.

Sem certificado Apple/notarizacao e certificado Authenticode, macOS e Windows podem exibir avisos de seguranca na primeira instalacao. Isso nao afeta o uso local, mas assinatura de distribuicao sera uma etapa posterior antes de entregar publicamente a clientes.

## Seguranca

- Nenhuma credencial e embutida no binario ou release.
- O sidecar mantem os endpoints mutaveis protegidos por origem loopback e CSRF.
- A janela bloqueia navegacao para enderecos externos nao autorizados.
- Logs nao imprimem tokens, recovery key, Chat ID nem payloads de credenciais.
- O app nao coleta telemetria nem envia o conteudo do carrossel para terceiros.

## Compatibilidade e migracao

- `./start.sh`, `./novo.sh tweet`, `./novo.sh stories` e `./stop.sh` continuam disponiveis para desenvolvimento e Codex.
- O app desktop usa os mesmos templates e nao cria uma segunda implementacao.
- Sessoes de HUB seguem efemeras no sentido de nao existir historico visivel; arquivos necessarios para recarregar a sessao atual sobrevivem ao ciclo de vida do processo.
- O estado dos editores no navegador embedded permanece local por sessao.

## Plano de implementacao

1. Tornar configuraveis o diretorio de dados, logs e caminhos de credenciais para o modo desktop, sem alterar o comportamento CLI atual.
2. Criar um entrypoint Python proprio para sidecar e um health check explicito.
3. Adicionar o projeto Tauri que inicia, monitora e encerra o sidecar.
4. Empacotar o sidecar Python com todos os recursos estaticos exigidos.
5. Adicionar script de desenvolvimento que abre a janela desktop contra o mesmo editor local.
6. Adicionar configuracao de build para macOS e Windows e workflow do GitHub Actions para gerar os artefatos privados.
7. Documentar instalacao, primeiro uso, restauracao de credenciais, atualizacao e solucao de problemas para usuarios sem familiaridade tecnica.

Cada etapa sera entregue em commit independente e reversivel.

## Criterios de aceite

1. O app abre uma janela nativa e chega ao HUB sem iniciar terminal ou browser.
2. Tweet e Stories iniciam, editam e mantem todas as funcoes atuais.
3. Colar imagem, mover blocos, undo e exportacao PNG funcionam no app.
4. Envio ao Telegram funciona depois da restauracao local das credenciais.
5. O app e inutilizavel externamente pela rede; o servidor fica em loopback.
6. Nenhum segredo aparece no pacote, no release, no HTML, no log ou no Git.
7. O pacote macOS e gerado e instalado localmente em uma maquina Mac.
8. O workflow produz instalador Windows a partir de runner Windows.
9. A suite Python, a verificacao de recursos empacotados e um smoke test do sidecar passam antes de cada release.

## Fora do escopo

- Assinatura Apple, notarizacao ou Authenticode nesta primeira entrega.
- Publicacao automatica na loja Apple ou Microsoft.
- Conta, login, banco de dados, historico, biblioteca ou nuvem.
- Sincronizacao entre dispositivos.
- Novos templates ou mudancas de funcionalidade no editor.
