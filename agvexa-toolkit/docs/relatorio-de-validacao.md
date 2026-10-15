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
| Testes unitários Python: **89 testes** | Testado e aprovado | detalhes abaixo |
| `validate-config.sh` do projeto | Testado e aprovado | 0 erros; 1 aviso esperado (manifesto real ainda não criado) |
| Sintaxe PowerShell com `pwsh` | **Não testado** | pwsh não instalado; coberto parcialmente pela análise estática |

Testes unitários:

| Módulo | Testes | Cobre |
|---|---|---|
| `test_ventoy_config.py` | 21 | `ventoy.json` gerado = versionado; UTF‑8 sem escapes; política de segurança; rejeição de BOM, JSON inválido, opção não documentada, valor fora da faixa, tipo errado, timeout, bypass Win11, plugin desconhecido, caminho relativo, barra final, alias longo, tema ausente, `default_file` inválido, `menu_class` ambíguo; modo ASCII |
| `test_theme.py` | 24 | os dois temas válidos e com versão; analisador de `theme.txt`; erros de chaves, propriedades, cores, imagens; PNG entrelaçado/16 bits/paleta/inválido recusados; ícones de todas as classes; menu F6 válido, comandos de boot proibidos, chaves desbalanceadas |
| `test_isos_and_staging.py` | 25 | status VERIFICADA/DIVERGENTE/NAO_VERIFICADA/TIPO_INVALIDO/AUSENTE/TAMANHO_DIVERGENTE/DESABILITADA/NAO_CATALOGADA; checksums oficiais GNU e BSD; detecção MBR/GPT; cache; staging só com verificadas; `[NÃO VERIFICADA]`; DIVERGENTE nunca entra; layout; SHA256SUMS; links; pastas de apoio e extras/; recusa de CLIENTES; `--dry-run`; recusas (fora de `build/`, `/dev`, link simbólico, diretório não marcado) |
| `test_security.py` | 7 | varredura de comandos destrutivos (shell, Python, PowerShell), catálogo do Optimizer, autoteste do próprio scanner, ausência de arquivos grandes/ISOs, `.gitignore` |
| `test_powershell_static.py` | 12 | BOM UTF‑8, cabeçalhos/ajuda, WhatIf, blocos balanceados, ausência de sintaxe exclusiva do PS7, padrão "somente análise", ordem dos 12 passos, opções do menu, versão, catálogo |

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
| BIOS legado | **Não testado** / Dependente de hardware físico |
| Secure Boot | **Não testado** / Dependente de hardware físico |
| Resoluções, pouca RAM, HD/SSD/NVMe | **Não testado** / Dependente de hardware físico |
| Boot de cada ferramenta pelo Ventoy | **Não testado** (nenhuma ISO real baixada) |

## 4. Windows Optimizer

| Teste | Resultado |
|---|---|
| Análise estática no Linux | Testado e aprovado |
| Sintaxe pelo parser do PowerShell | **Não testado** |
| Execução em Windows 10/11 (sem e com privilégios, análise, simulação, WhatIf, reversão, repetição, erros, relatórios) | **Não testado** — plano W‑1 a W‑13 em `windows-optimizer.md` |

**Versões do Windows efetivamente testadas: nenhuma.**

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
