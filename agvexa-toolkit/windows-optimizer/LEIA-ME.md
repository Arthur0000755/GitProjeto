# AG Vexa Windows Optimizer

Scripts PowerShell de preparação pós-formatação do Windows 10/11.
**Padrão: somente análise.** Nada muda sem avaliação, backup e confirmação.

> Versão 0.1.0-rc1 — ainda **não validada em Windows real**. Use primeiro em VM/laboratório.

Início rápido (PowerShell, nesta pasta):

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\AGVexa-Optimizer.ps1
```

| Arquivo | Função |
|---|---|
| `AGVexa-Optimizer.ps1` | menu principal |
| `Get-AGVexaSystemInfo.ps1` | diagnóstico (somente leitura) |
| `Test-AGVexaOptimization.ps1` | avaliação prévia por perfil |
| `Invoke-AGVexaOptimization.ps1` | aplicação dos ajustes aprovados (`-Aplicar`, `-WhatIf`) |
| `Restore-AGVexaSettings.ps1` | reversão a partir do backup da sessão |
| `New-AGVexaReport.ps1` | relatório técnico local (HTML/Markdown) |
| `lib/AGVexa.Common.psm1` | funções comuns (sessão, backup, ajustes) |
| `profiles/ajustes.json` | catálogo de ajustes e perfis |
| `assets/agvexa-logo.png` | logomarca usada no relatório HTML |
| `tests/` | autoteste sem dependências e testes Pester 5 |

Manual completo: `AGVexa/docs/windows-optimizer.md` (no HD) ou `docs/windows-optimizer.md` (no projeto).
