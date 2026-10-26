# Relatório de validação — AG Vexa Toolkit 0.1.0-rc1

Data: 2026-10-14 · Ambiente: contêiner Linux de desenvolvimento (Ubuntu 24.04.5,
Python 3.13, Pillow e PyYAML disponíveis; **sem** QEMU, OVMF, pwsh, shellcheck, rsync).

Classificação: **Testado e aprovado · Testado com ressalvas · Falhou · Não testado · Dependente de hardware físico.**

## 1. Testes automatizados — `tests/run-all.sh`

Resultado: **22 verificações passaram, 0 falharam, 2 puladas.**

| Grupo | Resultado | Detalhe |
|---|---|---|
| `bash -n` em todos os `.sh` (8 arquivos) | Testado e aprovado | |
| shellcheck | **Não testado** | ferramenta não instalada |
| `--help` e rejeição de opção inválida (código 64) em 6 scripts | Testado e aprovado | |
| Testes unitários Python: **96 testes** | Testado e aprovado | detalhes abaixo |
| `validate-config.sh` do projeto | Testado e aprovado | 0 erros; 1 aviso esperado (manifesto real ainda não criado) |
| Sintaxe PowerShell com `pwsh` | **Não testado** | pwsh não instalado; coberto parcialmente pela análise estática |

Testes unitários:

| Módulo | Testes | Cobre |
|---|---|---|
| `test_ventoy_config.py` | 21 | `ventoy.json` gerado = versionado; UTF‑8 sem escapes; política de segurança; rejeição de BOM, JSON inválido, opção não documentada, valor fora da faixa, tipo errado, timeout, bypass Win11, plugin desconhecido, caminho relativo, barra final, alias longo, tema ausente, `default_file` inválido, `menu_class` ambíguo; modo ASCII |
| `test_theme.py` | 24 | os dois temas válidos e com versão; analisador de `theme.txt`; erros de chaves, propriedades, cores, imagens; PNG entrelaçado/16 bits/paleta/inválido recusados; ícones de todas as classes; menu F6 válido, comandos de boot proibidos, chaves desbalanceadas |
| `test_isos_and_staging.py` | 25 | status VERIFICADA/DIVERGENTE/NAO_VERIFICADA/TIPO_INVALIDO/AUSENTE/TAMANHO_DIVERGENTE/DESABILITADA/NAO_CATALOGADA; checksums oficiais GNU e BSD; detecção MBR/GPT; cache; staging só com verificadas; `[NÃO VERIFICADA]`; DIVERGENTE nunca entra; layout; SHA256SUMS; links; pastas de apoio e extras/; recusa de CLIENTES; `--dry-run`; recusas (fora de `build/`, `/dev`, link simbólico, diretório não marcado) |
| `test_security.py` | 7 | varredura de comandos destrutivos (shell, Python, PowerShell), catálogo do Optimizer, autoteste do próprio scanner, ausência de arquivos grandes/ISOs, `.gitignore` |
| `test_powershell_static.py` | 16 | BOM UTF‑8, nomes de função × aliases padrão, `$PSScriptRoot` fora de `param()`, `-Include` com `-LiteralPath`, cabeçalhos/ajuda, verificador da cópia (`Verificar-Copia.ps1`), WhatIf, blocos balanceados, ausência de sintaxe exclusiva do PS7, padrão "somente análise", ordem dos 12 passos, opções do menu, versão, catálogo |

## 2. Ensaios manuais (linha de comando)

| Ensaio | Resultado |
|---|---|
| `preflight.sh` | Testado e aprovado (código 2 = avisos: ferramentas opcionais ausentes, execução como root no contêiner, manifesto real ausente) |
| `prepare-staging.sh --iso-mode none` + `validate-config.sh --staging` | Testado e aprovado (127 ações; 784 KiB; 0 erros) |
| Fluxo completo com 3 ISOs **sintéticas** (arquivos de teste com assinatura ISO 9660): `verify-isos.sh` → `prepare-staging.sh` (links) → `validate-config.sh --staging` → `sha256sum -c` | Testado e aprovado: 2 VERIFICADAS incluídas com nomes amigáveis; 1 DIVERGENTE ignorada; cópia íntegra |
| `test-boot.sh --check` / `--plan` | Testado e aprovado (código 2: dependências ausentes; plano exibido sem executar nada) |
| `test-boot.sh --vm --image /dev/sda` | Testado e aprovado (recusado, código 64) |
| `prepare-staging.sh --output /tmp/x` | Testado e aprovado (recusado, código 64) |
| `novo-relatorio.sh` | Testado e aprovado |
| `build-theme-assets.py` | Testado e aprovado (imagens 8 bits RGB/RGBA sem entrelaçamento) |

## 3. Boot e hardware

| Cenário | Resultado |
|---|---|
| Renderização real do tema no GRUB/Ventoy | **Não testado** — a prévia em `docs/previews/` é uma simulação Pillow |
| UEFI x86_64 | **Não testado** / Dependente de hardware físico |
| BIOS legado — notebook STI 1414, Ventoy 1.1.17 e 1.1.18 (2026-10-26) | **Falhou** com o tema principal: `unaligned pointer 0x15e33 / Aborted`. Ventoy sem `ventoy.json` e tema leve: menu aparece. Causa encontrada por eliminação (ver abaixo); correção **aguardando reteste** |
| Secure Boot | **Não testado** / Dependente de hardware físico |
| Resoluções, pouca RAM, HD/SSD/NVMe | **Não testado** / Dependente de hardware físico |
| Boot de cada ferramenta pelo Ventoy | **Não testado** (nenhuma ISO real baixada) |

**Primeiro boot real — diagnóstico do `unaligned pointer`**

Por eliminação, com variantes do `ventoy.json`: Ventoy puro funciona; controle, nomes,
ícones e dicas funcionam isolados; o tema leve funciona; o tema principal falha mesmo
sozinho, com fundo RGB ou RGBA. Causa: posições com casa decimal (`left = 5.5%`,
`width = 60.5%` no tema e `"left": "5.5%"` no `menu_tip`). O GRUB lê posições com
`grub_strtoul` (`parse_proportional_spec`, `gfxmenu/theme_loader.c`), que só aceita inteiros;
o erro de leitura leva o Ventoy a abortar. Correção: valores inteiros (`6%`, `60%`) e o
validador passa a recusar decimais (antes os aceitava).

## 4. Windows Optimizer

| Teste | Resultado |
|---|---|
| Análise estática no Linux | Testado e aprovado |
| Autoteste `Invoke-AGVexaSelfTest.ps1` como administrador — 2026-10-23, Windows 10 build 17763 (Enterprise LTSC), PowerShell 5.1.17763 | 1ª execução: 36 passou, 8 falhou, 1 pulado (causas abaixo). **Reexecução após correções (2026-10-23): Testado e aprovado — 38 passou, 0 falhou, 1 pulado** (`-CicloReal`, só em VM). **Após a correção do `-WhatIf` (PR #6): 39 passou, 0 falhou, 1 pulado** |
| Autoteste como usuário comum — 2026-10-23, mesma estação | **Testado e aprovado** — 38 passou, 0 falhou, 1 pulado; ajustes que exigem admin corretamente ignorados |
| Execução completa em Windows 10/11 (análise, simulação, WhatIf, reversão, repetição, erros, relatórios) | **Não testado** — plano W‑1 a W‑13 em `windows-optimizer.md` |

Falhas da primeira execução real e correções:

1. Sintaxe e codificação (6 falhas): o autoteste também conferia `LEIA-ME.md`, `ajustes.json` e
   `agvexa-logo.png`, porque `Get-ChildItem -LiteralPath ... -Include` ignora o `-Include` no
   PowerShell 5.1. Os scripts em si passaram. Correção: filtro pela extensão.
2. Relatório HTML/Markdown e `-Aplicar -WhatIf` (2 falhas): a função auxiliar `H` de
   `New-AGVexaReport.ps1` era encoberta pelo alias padrão `h` (`Get-History`), que tem precedência
   sobre funções. Correção: função renomeada para `ConvertTo-AGVexaHtml`.

Os dois casos ganharam testes estáticos (nomes de função × aliases padrão; `-Include` com `-LiteralPath`).

**Verificador da cópia** (`VERIFICAR-COPIA.cmd`)

| Teste | Resultado |
|---|---|
| Pasta de teste — 2026-10-23, mesma estação | **Testado e aprovado**: cópia íntegra, arquivo alterado (`[FALHOU]`), arquivo ausente (`[AUSENTE]`), recuperação e lista ausente (`[ERRO]`). `-SemISOs` chamado direto com `powershell -File`: **falhou** (`$PSScriptRoot` vazio no valor padrão de `-Raiz`, PS 5.1); corrigido e **retestado: aprovado** (4 conferidos, ISOs puladas, caminho sem `\.`; o próprio script substituído apareceu como `[FALHOU]`, como esperado) |

**Versões do Windows efetivamente testadas: Windows 10 Enterprise LTSC build 17763 (autoteste do Optimizer como administrador e como usuário comum, e verificador da cópia; aprovados).**

## 5. Critérios de aceitação (seção 16 do pedido)

| Critério | Situação |
|---|---|
| Estrutura do repositório completa | ✅ atendido |
| Tema personalizado com arquivos reais | ✅ atendido (PNG reais; renderização real não testada) |
| Configuração do Ventoy com recursos documentados | ✅ atendido (confirmados no código-fonte 1.1.18) |
| Catálogo de ferramentas documentado | ✅ atendido |
| Scripts funcionais de verificação | ✅ atendido |
| Staging sem formatar dispositivos | ✅ atendido |
| Testes automatizados disponíveis passando | ✅ atendido (shellcheck e pwsh não disponíveis) |
| Dependências identificadas | ✅ atendido (`preflight.sh`, este relatório) |
| Riscos documentados | ✅ atendido |
| Nenhuma alteração em outros sistemas | ✅ atendido |
| Instalação física claramente pendente | ✅ atendido (Fase F apenas documentada) |
| Nenhum teste não executado declarado aprovado | ✅ atendido (tabelas acima) |

**Conclusão:** versão **candidata para homologação técnica acompanhada**. Não
está pronta para uso em clientes antes dos testes de boot (VM/hardware) e dos
testes do Optimizer em Windows.

## 6. Como reproduzir

```bash
bash scripts/preflight.sh
bash scripts/test-boot.sh          # roda tests/run-all.sh e verifica dependências de VM
bash scripts/prepare-staging.sh --iso-mode none
bash scripts/validate-config.sh --staging build/staging
```
