# HUB local de templates para clientes

## Objetivo

Transformar o editor local de carrosséis em um HUB distribuído por um repositório privado no GitHub. O cliente clona o projeto, opera a ferramenta localmente com auxílio do Codex e utiliza apenas os templates oficiais disponíveis.

O fluxo deve preservar integralmente os recursos já validados dos editores Tweet e Stories. A ferramenta é central na produção atual, portanto o HUB será uma camada nova ao redor desses editores, não uma reescrita deles.

## Princípios

- Preservar primeiro, evoluir depois.
- Manter o produto local, simples e sem autenticação.
- Não criar histórico, biblioteca, conta ou banco de dados.
- Não permitir que clientes criem ou alterem templates.
- Manter credenciais e configurações pessoais fora do Git.
- Adicionar templates futuros por um contrato explícito, sem espalhar condições pelo servidor.
- Introduzir mudanças pequenas, testáveis e reversíveis.

## Experiência do usuário

Ao abrir `http://localhost:8777`, o usuário encontra a tela `Editor de Carrosséis`. Ela apresenta somente os templates oficiais ativos.

Cada cartão contém:

- miniatura representativa;
- nome do template;
- proporção;
- quantidade inicial de slides;
- ação `Criar carrossel`.

Fluxo:

```text
Abrir HUB
→ escolher Tweet ou Stories
→ receber uma criação nova e limpa
→ editar
→ exportar PNGs ou enviar ao Telegram
→ descartar e voltar ao HUB
```

A tela não terá dashboard, métricas, projetos recentes, onboarding, menu lateral ou configurações administrativas.

## Catálogo inicial

### Tweet

- 10 slides iniciais;
- proporção principal 4:5;
- editor atual preservado;
- usuário pode adicionar ou remover slides.

### Stories

- 10 slides iniciais;
- proporção 4:5 (1080×1350), preservando a geometria validada do editor;
- editor atual preservado;
- usuário pode adicionar ou remover slides.

O número de 10 slides para Stories deve ser aplicado ao comportamento real, ao gerador, ao template, à interface, à documentação, aos exemplos e aos testes. Não será apenas um texto exibido no HUB.

## Sessões efêmeras

Cada clique em `Criar carrossel` cria uma sessão temporária independente no diretório local do editor. O fluxo do HUB não cria rascunho Markdown em `content/rascunhos/`.

A sessão pode manter estado local suficiente para sobreviver a uma recarga acidental da página atual. Esse estado não será apresentado como histórico e não poderá reaparecer ao iniciar uma criação nova.

Ao voltar ao HUB, a interface deve deixar claro que a criação atual será descartada. Ao iniciar o servidor, o sistema remove todos os HTMLs de sessão criados pelo HUB na execução anterior. HTMLs gerados pelos comandos técnicos existentes usam outra identificação e não entram nessa limpeza.

## Arquitetura

### 1. HUB

Nova página inicial servida em `/`. Ela lê um catálogo interno de templates ativos e oferece a ação de criação. A página não conhece detalhes internos de Tweet ou Stories.

### 2. Catálogo de templates

Uma fonte central define, para cada template:

- identificador estável;
- nome público;
- descrição curta;
- proporção;
- quantidade inicial de slides;
- miniatura;
- template HTML usado pelo gerador;
- disponibilidade.

O catálogo é a única fonte para montar o HUB e validar solicitações de criação. Templates não cadastrados não podem ser iniciados pelo cliente.

### 3. Criador de sessão

O servidor recebe a escolha de um template oficial, cria uma identidade temporária, gera o HTML com conteúdo padrão e redireciona o navegador para essa sessão.

O criador reutiliza o gerador atual e não duplica a montagem de Tweet ou Stories.

### 4. Editores existentes

Tweet e Stories mantêm seus fluxos atuais de edição, undo, perfil, imagens, exportação e Telegram. A primeira versão do HUB não exige extrair ou reescrever os HTMLs monolíticos.

### 5. Serviços compartilhados

Exportação PNG e envio ao Telegram continuam disponíveis. As credenciais do Telegram ficam exclusivamente no servidor local; o navegador envia os PNGs a endpoints locais protegidos e recebe apenas o estado configurado/não configurado. Essa centralização preserva o comportamento já validado sem expor Bot Token ou Chat ID ao HTML.

## Fluxo de dados

```text
Catálogo oficial
    ↓
HUB seleciona template
    ↓
Servidor valida identificador
    ↓
Gerador cria HTML temporário com 10 slides
    ↓
Editor preserva estado apenas da sessão atual
    ↓
PNG local ou envio ao Telegram
```

Nenhum conteúdo da criação é enviado ao GitHub. O GitHub distribui somente código, templates oficiais, ativos e atualizações.

## Telegram e credenciais

- O cliente pode exportar PNGs localmente.
- O cliente pode enviar o carrossel ao bot do Telegram usando a configuração local existente.
- Tokens, Chat ID e outras credenciais não entram no repositório em texto puro.
- Bot Token e Chat ID não são servidos ao navegador nem gravados no armazenamento web.
- O servidor escuta somente em `127.0.0.1`; mutações exigem origem local válida e token efêmero de sessão.
- Descartar pelo HUB remove somente o HTML e o armazenamento da sessão atual. O fluxo técnico direto permanece intacto.
- Ausência ou erro de configuração deve mostrar orientação clara sem impedir exportação em PNG.
- O HUB não exibe nem manipula segredos.

## Remoção completa do modo Ostentação

O modo `ostentacao` será removido do projeto após uma auditoria de dependências. A remoção inclui:

- `templates/ostentacao_editor.html`;
- opção de template no gerador e na CLI;
- defaults e fallbacks associados;
- documentação e exemplos;
- testes e referências internas;
- qualquer rota ou comando que o exponha.

A exclusão será isolada em uma etapa própria. Antes dela, os testes de Tweet e Stories deverão cobrir explicitamente os comportamentos que não podem regredir. O histórico do Git permanece como mecanismo de recuperação.

## Compatibilidade e atualização

Os comandos técnicos permanecem disponíveis:

```bash
./start.sh
./novo.sh tweet
./novo.sh stories
./stop.sh
```

O cliente atualiza o produto com `git pull`. Arquivos locais, credenciais e configurações ignoradas pelo Git não são sobrescritos pela atualização.

As URLs diretas de editores gerados continuam funcionando durante a transição. A mudança principal é que `/` passa a ser o HUB, em vez de redirecionar automaticamente ao HTML mais recente.

## Erros e recuperação

- Template inexistente ou inativo: retornar erro amigável e manter acesso ao HUB.
- Falha na geração: não criar sessão parcial; registrar o erro localmente e oferecer nova tentativa.
- Telegram indisponível: preservar o editor e permitir exportação PNG.
- Recarregamento: restaurar apenas a sessão atual.
- Atualização que não reconhece um identificador de template: recusar a criação, manter o HUB disponível e não alterar credenciais locais.
- Regressão em Tweet ou Stories: impedir integração enquanto os testes ou a validação visual falharem.

## Estratégia de implementação segura

1. Registrar o comportamento atual com testes e HTMLs de referência.
2. Alterar Stories de 17 para 10 slides de forma completa e testada.
3. Auditar e remover Ostentação em mudança isolada.
4. Introduzir o catálogo oficial sem alterar os editores.
5. Criar o endpoint de sessão temporária.
6. Criar a página do HUB e integrá-la ao servidor.
7. Validar Tweet e Stories ponta a ponta: criação, edição, undo, PNG e Telegram.
8. Atualizar instalação, uso e fluxo de atualização no README.

Cada fase deve produzir um commit reversível. Nenhuma refatoração compartilhada é requisito para lançar o HUB.

## Testes e critérios de aceite

1. A raiz `localhost:8777` apresenta o HUB sem listagem de diretório ou redirecionamento para trabalho anterior.
2. O HUB apresenta somente Tweet e Stories.
3. Tweet e Stories iniciam com exatamente 10 slides.
4. Uma nova criação nunca recupera conteúdo de uma sessão anterior.
5. Recarregar uma sessão atual preserva sua edição em andamento.
6. Nenhum rascunho Markdown é criado pelo fluxo do HUB.
7. Adicionar e remover slides continua funcionando nos dois editores.
8. Undo continua funcionando nos dois editores.
9. Exportação PNG continua funcionando e mantém fidelidade visual.
10. Envio ao Telegram continua funcionando com configuração válida.
11. Falha no Telegram não bloqueia a exportação PNG.
12. Não existe referência executável ao modo Ostentação.
13. Segredos e configurações pessoais permanecem fora do Git.
14. Os comandos técnicos existentes continuam operantes.
15. `python3 -m py_compile scripts/*.py`, a suíte automatizada e a validação HTTP em `localhost:8777` passam antes da integração.

## Fora do escopo

- Histórico de carrosséis.
- Projetos recentes ou biblioteca.
- Login, permissões ou contas de cliente.
- Banco de dados ou armazenamento em nuvem.
- Marketplace de templates.
- Criação ou alteração de templates pelo cliente.
- Publicação direta no Instagram.
- Reescrita dos editores em framework frontend.
- Sincronização de conteúdo entre computadores.
