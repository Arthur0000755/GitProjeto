# Relatório de segurança — AG Vexa Toolkit 0.1.0-rc1

Data: 2026-10-14

## 1. Alterações fora do projeto

**Nenhuma.** Todo o trabalho ficou no diretório `agvexa-toolkit/` do repositório
Git dedicado (branch de desenvolvimento). Detalhe importante: o desenvolvimento
ocorreu num **contêiner de nuvem isolado** (Ubuntu 24.04), não no servidor da AG Vexa.
Portanto não houve contato com Docker, MAPOS, Nginx, Cloudflare, bancos de dados,
systemd, AG Vexa Prospect ou qualquer serviço do servidor.

Não foram executados: formatação, particionamento, instalação de bootloader,
`sudo`, instalação de pacotes, download de ISOs, uso de APIs pagas, exposição de
serviços. O único acesso de rede foi a leitura do código-fonte público do Ventoy
(clone raso em diretório temporário, fora do projeto, não versionado).

## 2. Controles implementados

### Scripts do servidor (`scripts/`)

| Controle | Implementação | Teste |
|---|---|---|
| Sem acesso a dispositivos | `agv_refuse_device_path` recusa `/dev`, `/proc`, `/sys`, `/run` e dispositivos de bloco; Python nunca abre `/dev` | `test_security.py`; teste manual com `/dev/sda` → código 64 |
| Sem comandos destrutivos/privilegiados | varredura estática proíbe `sudo`, `mkfs`, `wipefs`, `parted`, `fdisk`, `dd of=`, `losetup`, `mount`, `Ventoy2Disk`, `systemctl`, `docker`, `curl`/`wget`, `apt/pip install` fora de textos de ajuda | `test_shell_scripts_have_no_destructive_commands` |
| Python sem processos/rede | proíbe `subprocess`, `os.system`, `socket`, `urllib`, `requests`, `ctypes` em `scripts/` | `test_python_has_no_process_or_network_access` |
| Staging isolado | só dentro de `build/`; recusa link simbólico, ponto de montagem e diretório não marcado; só apaga staging com marcador `.agvexa-staging` | `StagingTests` (6 testes de recusa) |
| `--dry-run` | staging e regeneração do `ventoy.json` | `test_dry_run_writes_nothing` |
| Integridade das ISOs | SHA‑256 oficial obrigatório para VERIFICADA; DIVERGENTE nunca entra no staging, nem com `--allow-unverified`; sem checksums fictícios | `IsoVerificationTests`, `test_example_manifest_has_no_fake_checksums` |
| Conferência pós-cópia | `SHA256SUMS-AGVEXA.txt` compatível com `sha256sum -c` | `test_checksums_cover_isos`; ensaio manual |
| Teste em VM | imagem só arquivo comum, `-snapshot`, sem rede, 1 vCPU, `nice`; VNC só em 127.0.0.1 | revisão de código (QEMU indisponível) |

### Configuração de boot

| Controle | Valor | Verificado por |
|---|---|---|
| Sem boot automático | sem `VTOY_MENU_TIMEOUT`/`VTOY_DEFAULT_IMAGE` | validador (erro de POLÍTICA) |
| Sem bypass do Windows 11 | `VTOY_WIN11_BYPASS_CHECK=0`, `..._NRO=0` | validador |
| Secure Boot | `VTOY_SECURE_BOOT_POLICY=1` (seguir firmware) | validador (aviso se diferente) |
| Menu F6 | só `echo/read/clear/set/if/smbios/reboot/halt/sleep` | validador (lista de comandos permitidos) |
| Ferramentas inexistentes | pastas sem ISO ocultas pelo Ventoy; aliases só de ISOs presentes | código do Ventoy + `test_only_verified_isos_are_staged` |

### Windows Optimizer

| Controle | Implementação |
|---|---|
| Padrão somente análise | sem `-Aplicar` nada é alterado; `-WhatIf` suportado |
| Confirmação | digitar `APLICAR` / `RESTAURAR` |
| Backup antes de cada mudança | registro gravado em `backup.json` **antes** da alteração; verificação após |
| Proibições | varredura estática bloqueia desativar Defender/Firewall/Update/UAC/BitLocker, `Set-ExecutionPolicy` permanente, `Invoke-Expression`, downloads, remoção de apps, formatação, `Remove-Item -Recurse` (exceto diretório temporário do autoteste), escrita em chaves protegidas |
| Catálogo restrito | ajustes de registro só em `HKCU`; teste rejeita chaves de políticas/segurança |
| Privacidade | sem nome do computador, usuário, série ou chave do produto por padrão; caminhos de perfil mascarados |
| Sem rede | nenhum download/envio; relatório local |

## 3. Regras operacionais documentadas

`manual-do-tecnico.md` (Parte 1), menu F6 "Regras de segurança", painel do fundo
do tema, dicas por categoria e checklists em `templates/relatorios/`.

## 4. Riscos residuais

Ver `riscos-e-limitacoes.md`. Principal: o erro humano na escolha de disco em
ferramentas de terceiros — mitigado por procedimento, não por código.
