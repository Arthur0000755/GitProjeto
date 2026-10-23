# PROGRESSO — AG Vexa Toolkit

Arquivo para retomar o desenvolvimento em outra conversa. Atualize a cada fase.

## Estado em 2026-10-14 — versão 0.1.0-rc1

| Fase | Situação |
|---|---|
| A — Pesquisa e arquitetura | ✅ concluída (Ventoy 1.1.18 confirmado no código-fonte; `docs/arquitetura.md`) |
| B — Personalização visual | ✅ concluída (temas `agvexa` e `agvexa-lite`, 18 ícones, fundos; renderização real **não testada**) |
| C — Biblioteca e preparação | ✅ concluída (catálogo, manifesto, verificação SHA‑256, staging) |
| D — Testes automatizados | ✅ concluída para o disponível (93 testes unitários + 22 verificações; VM/pwsh/shellcheck indisponíveis) |
| E — Documentação e entrega | ✅ concluída (manual, procedimentos, checklists, relatórios) |
| Complemento — Windows Optimizer | ✅ implementado; autoteste aprovado no Windows 10 LTSC 17763 como admin e como usuário comum (38/0; 39/0 após a correção do `-WhatIf`); faltam W‑1 a W‑13 em VM |
| F — Instalação no HD real | ⛔ NÃO executada (aguarda autorização) |

## Onde o projeto está

- Repositório Git dedicado `GitProjeto`, pasta `agvexa-toolkit/`, branch de desenvolvimento
  `ccr-177553c9-k5x8xf`. No servidor, clone e use (ou crie um link) em `~/agvexa-toolkit`:
  `git clone <url> ~/GitProjeto && ln -s ~/GitProjeto/agvexa-toolkit ~/agvexa-toolkit`.
- Os scripts encontram a raiz do projeto sozinhos (funcionam em qualquer caminho).

## Próximos passos (em ordem)

1. No servidor: `bash scripts/preflight.sh` e `bash scripts/test-boot.sh`.
2. Baixar as ISOs oficiais, preencher `catalog/isos-manifest.json` com SHA‑256 **oficiais**, `verify-isos.sh`.
3. (Com autorização) instalar QEMU/OVMF ou usar outro computador; executar `test-boot.sh --plan` e VM‑1 a VM‑9.
4. Testar o Windows Optimizer: primeiro o autoteste na estação Windows 10 Enterprise LTSC
   (`docs/uso-no-windows.md` §8), depois W‑1 a W‑13 em VM.
5. Ajustar tema conforme capturas reais.
6. Preparar o HD de 1 TB: SMART, cópia de segurança, criptografia e organização (`docs/hd-arquivo-1tb.md`).
7. Fase F no HD de **320 GB** com o proprietário (`docs/instalacao-segura.md`), depois testes HW‑1 a HW‑5.

## Pendências que exigem decisão do proprietário

1. **Instalar ferramentas de teste** no servidor (qemu-system-x86, ovmf, shellcheck, powershell) ou usar outro computador para testes de VM.
2. **Windows 10** na mídia: incluir ou não (fim do suporte regular em 14/10/2025).
3. **Secure Boot em clientes**: política preferida (desativar temporariamente × registrar chave do Ventoy com autorização do cliente).
4. **Licença dos arquivos próprios** (documentação, temas, scripts).
5. **Integração MAPOS**: se/quando (`docs/integracao-mapos-futura.md`).

## Decisões já tomadas (não reabrir sem motivo)

- Ventoy, plugins oficiais apenas; MBR na instalação; Secure Boot "seguir firmware".
- ISOs só VERIFICADAS por padrão; sem boot automático; sem bypass do Windows 11.
- Tema 1024×768 com fonte padrão do Ventoy; textos grandes renderizados no fundo.
- Optimizer: padrão análise; só ajustes documentados e reversíveis; startup sempre manual.
- Discos (2026-10-15): **HD 320 GB = toolkit** (Ventoy, sem `-r`); **HD 1 TB = arquivo da empresa**
  (documentos, cópia mestre do toolkit, backups de clientes), criptografado, fica na bancada
  (`docs/hd-arquivo-1tb.md`).

## Histórico

- 2026-10-14 — 0.1.0-rc1: implementação inicial das Fases A–E e do Windows Optimizer.
- 2026-10-15 — logomarca oficial integrada ao tema do boot, papéis de parede e relatório do Optimizer.
- 2026-10-21 — guia `docs/uso-no-windows.md` (estação Windows 10 Enterprise LTSC: Ventoy2Disk.exe, cópia, conferência, autoteste do Optimizer).
- 2026-10-15 — decisão de discos: 320 GB = toolkit; 1 TB = arquivo criptografado da empresa com backups de clientes.
- 2026-10-23 — 1º autoteste do Optimizer em Windows real (LTSC build 17763): 36 ok / 8 falhas; causas corrigidas e reexecução aprovada (38 ok / 0 falhas).
- 2026-10-21 — verificador da cópia por duplo clique (`VERIFICAR-COPIA.cmd` + `AGVexa\Verificar-Copia.ps1`).
- 2026-10-15 — pastas de apoio (DRIVERS, INSTALADORES, FERRAMENTAS, BIOS_FIRMWARE) e política de dados de clientes fora da mídia.
