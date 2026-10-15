# Plano de testes de boot

Classificação obrigatória de cada resultado: **Testado e aprovado · Testado com
ressalvas · Falhou · Não testado · Dependente de hardware físico.**
Uma configuração validada por JSON **não** garante boot real.

## Nível 1 — Automatizado (servidor, sem privilégios)

`scripts/test-boot.sh` (executa `tests/run-all.sh`): sintaxe, unidades,
validação de configuração, varredura de segurança, staging em diretório
temporário. Resultado atual: ver `relatorio-de-validacao.md`.

## Nível 2 — Máquina virtual (imagem descartável)

Requer: QEMU + OVMF (instalação de pacotes exige autorização), e criar uma
imagem Ventoy em **dispositivo loop** (exige `sudo`). Procedimento completo:
`scripts/test-boot.sh --plan`.

Recursos modestos para não afetar o servidor: 1 vCPU, 1024 MiB, sem rede,
`nice`, imagem aberta com `-snapshot`. Com o Pentium T4500 sem KVM
disponível ao usuário, a VM é emulada (lenta): prefira executar fora do
horário de uso dos serviços, ou em outro computador.

| ID | Cenário | Comando | Critério de aprovação |
|---|---|---|---|
| VM-1 | UEFI, USB | `--vm --firmware uefi --bus usb --headless` | captura mostra o tema AG Vexa com as categorias presentes |
| VM-2 | BIOS, USB | `--vm --firmware bios --headless` | idem em BIOS |
| VM-3 | UEFI + Secure Boot (OVMF .ms) | `--vm --firmware uefi-sb` (interativo, `--vnc`) | MokManager aparece; após registrar a chave na VM, menu abre |
| VM-4 | Tema leve | F5 > Seleção de Tema | menu legível sem imagem de fundo |
| VM-5 | Modo texto | F5 > Modo de Exibição | menu navegável |
| VM-6 | Menu F6 | F6 | 4 telas informativas + reiniciar/desligar |
| VM-7 | Verificação de plugins | F5 > verificar configuração do plugin json | sem erros |
| VM-8 | Resoluções | `gfxmode` 800×600, 1024×768, 1920×1080 (F5) | layout sem sobreposição |
| VM-9 | Boot de cada ISO | entrar em cada ferramenta | a ferramenta inicia (UEFI e BIOS) |

## Nível 3 — Hardware físico (após a Fase F)

Mínimo recomendado antes de usar em clientes:

| ID | Equipamento | Por quê |
|---|---|---|
| HW-1 | Notebook/desktop UEFI recente (2018+) com Secure Boot | cenário mais comum |
| HW-2 | Equipamento antigo só BIOS (≈2008–2012) | compatibilidade legada |
| HW-3 | Equipamento com NVMe | ferramentas Linux enxergam o disco? |
| HW-4 | Equipamento com 2 GB de RAM ou menos | ambientes live leves |
| HW-5 | Monitor/tela 1366×768 e 1920×1080 | tema e legibilidade |

Para cada equipamento, executar VM-4 a VM-9 e anotar na matriz de `compatibilidade.md`.
Não usar equipamentos de clientes para homologação.

## Nível 4 — Windows Optimizer

Ver `windows-optimizer.md`, seção "Plano de testes em Windows".
