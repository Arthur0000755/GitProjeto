# Compatibilidade

**Não há compatibilidade universal.** Firmwares de fabricantes diferentes
se comportam de formas diferentes. Este documento diz o que é esperado, o
que foi efetivamente testado e o que fazer quando algo não funciona.

## 1. Estado atual dos testes (0.1.0-rc1)

| Cenário | Situação |
|---|---|
| UEFI x86_64 | **Não testado** (dependente de hardware físico / VM) |
| BIOS legado | **Não testado** |
| Secure Boot | **Não testado** |
| Resoluções diferentes | **Não testado** em GRUB real; layout em percentuais; prévia aproximada em `docs/previews/` |
| Pouca memória RAM | **Não testado** |
| HD × SSD × NVMe (como alvo das ferramentas) | **Não testado** |
| Configuração (JSON/tema/F6) | Testado e aprovado por validação estática (ver `relatorio-de-validacao.md`) |

## 2. Expectativas por cenário

### UEFI x86_64 (preferencial)
- Escolha a entrada "UEFI: <nome do HD>" no menu de boot do firmware.
- Gráficos via GOP; tema principal em 1024×768.

### BIOS legado / CSM
- O Ventoy instalado em **MBR** (recomendação deste projeto) tem a maior compatibilidade.
- Algumas ISOs modernas só iniciam em UEFI (ex.: Windows 11 exige UEFI pelos requisitos oficiais).

### Secure Boot
Configuração do toolkit: `VTOY_SECURE_BOOT_POLICY = 1` (seguir a política do firmware).

1. Com Secure Boot ativo, o primeiro boot do Ventoy abre o **MokManager** (shim).
2. **Equipamentos da AG Vexa:** pode-se registrar a chave do Ventoy
   (*Enroll key from disk* → VTOYEFI → `ENROLL_THIS_KEY_IN_MOKMANAGER.cer`).
3. **Equipamentos de clientes:** registrar a chave altera o firmware do cliente.
   Só com autorização explícita. Alternativa: desativar o Secure Boot
   **temporariamente** no setup do firmware, usar a ferramenta e **reativar**
   antes da entrega. Registre no relatório.
4. Com a política "seguir firmware", ferramentas cujo carregador EFI não é
   assinado pela Microsoft/CA reconhecida **não iniciam** com Secure Boot ativo.
   Isso é proteção, não defeito. O toolkit **nunca** desativa proteções automaticamente.
5. Não instale certificados nem altere chaves (PK/KEK/db) de firmware.

### Resoluções
- `gfxmode` padrão: 1024×768 (mais compatível). Em telas largas, o firmware/monitor escala.
- Trocar no boot: **F5 > Configuração da Resolução**.
- Se o tema ficar lento ou distorcido: **F5 > Seleção de Tema > agvexa-lite**.
- Se nada gráfico funcionar: **F5 > Modo de Exibição da Tela > modo texto** (acentos podem
  aparecer incorretos em modo texto — limitação do Ventoy; o staging pode ser gerado com
  `--ascii-menu`).

### Pouca memória RAM
- O Ventoy carrega a ISO sem copiá-la inteira para a RAM no modo normal.
- Cada ferramenta tem requisitos próprios (ambientes live gráficos costumam pedir 2 GB ou mais).
  Em máquinas com 1–2 GB, prefira ferramentas em modo texto (Clonezilla, SystemRescue sem interface gráfica).

### Discos dos clientes (HD, SSD SATA, NVMe)
- NVMe exige suporte do kernel da ferramenta live (versões recentes suportam).
- Controladoras em modo RAID/Intel RST podem esconder discos NVMe de ferramentas Linux.
  **Não troque o modo SATA/RAID no firmware sem entender o impacto** (o Windows instalado pode
  deixar de iniciar). Registre e consulte.

## 3. Matriz para registrar testes físicos

Copie para `relatorio-de-validacao.md` ao testar:

| Equipamento (modelo) | Ano | Firmware | Secure Boot | Ferramenta | Resultado | Observações |
|---|---|---|---|---|---|---|
| | | UEFI/BIOS | on/off | | Aprovado / Com ressalvas / Falhou / Não testado | |
