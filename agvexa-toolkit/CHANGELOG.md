# Changelog — AG Vexa Toolkit

Formato baseado em "Keep a Changelog". Versões seguem SemVer.

## [Não lançado]

### Corrigido
- Pastas de categoria em `ISO/` sumiam ao compactar/copiar o staging (estavam vazias). Cada
  categoria agora tem um `LEIA-ME.txt` (o Ventoy ignora `.txt`; a categoria só aparece no menu
  quando recebe uma imagem).
- **Boot abortava com `unaligned pointer ... Aborted`** (primeiro teste real, BIOS legado):
  o tema principal e o `menu_tip` usavam posições decimais (`5.5%`, `60.5%`), que o GRUB não
  aceita. Agora são inteiros (`6%`, `60%`) e o validador recusa decimais em posições do tema e
  do `menu_tip`.
- `Verificar-Copia.ps1` chamado direto (`powershell -File ... -SemISOs`) falhava no PS 5.1:
  `$PSScriptRoot` fica vazio no valor padrão de `param()`. A pasta padrão agora é calculada no
  corpo do script, e a linha "Pasta" mostra o caminho sem `\.`. Novo teste estático.
- Optimizer com `-WhatIf` (ou sem nenhum ajuste aplicado): o passo 12/12 e o relatório não
  oferecem mais "Para desfazer"/"Como desfazer"; o relatório mostra o modo "WhatIf (nada alterado)".
  Autoteste ganhou a verificação correspondente.
- Windows Optimizer (primeira execução real, Windows 10 LTSC build 17763): relatório HTML/Markdown
  falhava porque a função `H` era encoberta pelo alias `h` (`Get-History`); renomeada para
  `ConvertTo-AGVexaHtml`. O autoteste conferia arquivos que não são PowerShell (`-Include` é
  ignorado com `-LiteralPath` no PS 5.1). Novos testes estáticos para os dois casos.

### Adicionado
- `VERIFICAR-COPIA.cmd` + `AGVexa/Verificar-Copia.ps1` na raiz da mídia: conferência da cópia por
  duplo clique no Windows (somente leitura; `-SemISOs` para conferência rápida).
- `docs/uso-no-windows.md`: fluxo servidor → Windows → HD (Ventoy2Disk.exe, cópia, conferência
  por PowerShell, teste de boot, autoteste do Optimizer na estação LTSC).
- `docs/hd-arquivo-1tb.md`: guia para criptografar e organizar o HD de 1 TB da empresa (arquivo +
  backups de clientes) sem perder dados. Toolkit passa a usar o HD de 320 GB.
- Pastas de apoio na raiz da mídia: `DRIVERS`, `INSTALADORES`, `FERRAMENTAS`, `BIOS_FIRMWARE`,
  com LEIA-ME de regras e `INVENTARIO.csv`; arquivos reais vêm de `extras/` (fora do Git).
- Staging e validador recusam pasta `CLIENTES`; procedimento de partição criptografada
  separada para dados de clientes (`docs/instalacao-segura.md`, seção 10).
- Logomarca oficial da AG Vexa (`branding/logo/agvexa-logo.png`) no fundo do tema do boot,
  nos papéis de parede e no relatório HTML do Windows Optimizer.

## [0.1.0-rc1] — 2026-10-14 — candidata para homologação

### Adicionado
- Arquitetura baseada em Ventoy 1.1.18, usando somente plugins oficiais
  (`control`, `theme`, `menu_alias`, `menu_class`, `menu_tip`) e menu F6 (`ventoy_grub.cfg`).
- Tema escuro **agvexa** (1024×768) e tema **agvexa-lite** (alternativo), 18 ícones originais,
  papéis de parede 1024×768 e 1920×1080, gerador reproduzível (`scripts/build-theme-assets.py`).
- Categorias 01–06 por pastas; pastas sem ISO ficam ocultas (comportamento nativo do Ventoy).
- Catálogo de ferramentas (`catalog/ferramentas.yaml`) e manifesto de ISOs com fonte oficial e SHA‑256.
- Scripts: `preflight.sh`, `validate-config.sh`, `verify-isos.sh`, `prepare-staging.sh`,
  `test-boot.sh`, `novo-relatorio.sh` — todos com `--help`, códigos de saída e sem acesso a dispositivos.
- Suíte de testes (`tests/run-all.sh`) com testes unitários e varredura estática de segurança.
- AG Vexa Windows Optimizer: menu, diagnóstico, avaliação, aplicação com backup, reversão,
  relatório; perfis Conservador, Desempenho e Personalizado; autoteste e testes Pester.
- Documentação em português: arquitetura, instalação segura (Fase F), manual do técnico,
  procedimentos de atendimento, compatibilidade, riscos, manutenção, licenças, segurança,
  plano de testes, relatório de validação; modelos de relatório.

### Pendente
- Testes de boot em VM e hardware físico; testes do Optimizer em Windows;
  download e verificação das ISOs reais; instalação no HD (Fase F).
