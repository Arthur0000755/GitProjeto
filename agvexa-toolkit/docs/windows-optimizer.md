# AG Vexa Windows Optimizer — Manual

Módulo do AG Vexa Toolkit para **preparação pós-formatação** e otimização
**segura e reversível** do Windows 10/11. Fica no HD em
`AGVexa/windows-optimizer/` e roda no Windows do cliente, sem instalar nada.

> **Situação desta versão (0.1.0-rc1): NÃO validado em Windows real.**
> Os scripts passaram por verificações estáticas no Linux (ver
> `relatorio-de-validacao.md`). Antes de usar em clientes, execute o plano
> de testes da seção 9 numa VM ou computador de laboratório.

## 1. O que ele faz e o que NUNCA faz

Faz: diagnóstico; avaliação prévia; até 6 ajustes documentados e reversíveis
(4 visuais por usuário, 2 de plano de energia); listas para revisão manual
(inicialização, serviços/tarefas de terceiros, apps da Loja); relatório local; reversão.

**Nunca:** desativa Microsoft Defender, Firewall, Windows Update, UAC ou
BitLocker; desativa paginação, restauração do sistema ou otimização/TRIM de SSD;
remove aplicativos; exclui arquivos; usa listas genéricas de "serviços
desnecessários"; baixa ou executa nada da internet; altera a política de
execução de forma permanente; promete ganhos de FPS/RAM/velocidade.

## 2. Como iniciar

1. Faça login **na conta que o cliente vai usar** (os ajustes visuais valem por usuário).
2. Abra o PowerShell (para ler BitLocker/Secure Boot/TPM: "Executar como administrador").
3. Execute (a política *Bypass* vale **só para este processo**):
   ```powershell
   cd E:\AGVexa\windows-optimizer        # letra do HD do toolkit
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\AGVexa-Optimizer.ps1
   ```
4. Se os arquivos vieram por download/zip e o Windows bloquear:
   `Get-ChildItem -Recurse | Unblock-File` (somente nesta pasta, conferida).

## 3. Menu

```
AG VEXA WINDOWS OPTIMIZER
1 — Diagnóstico do computador      (somente leitura)
2 — Otimização conservadora        (recomendada para clientes)
3 — Otimização de desempenho       (hardware limitado)
4 — Personalizar ajustes           (escolha item a item)
5 — Programas de inicialização     (revisão com o cliente)
6 — Relatório técnico              (HTML local)
7 — Desfazer alterações            (usa o backup da sessão)
8 — Sair
```

## 4. Perfis

| Ajuste | Conservador | Desempenho | Admin | Reversão |
|---|---|---|---|---|
| Animação ao minimizar/maximizar janelas (SPI_SETANIMATION) | ✔ | ✔ | não | valor anterior salvo |
| Efeitos de animação do Windows (SPI_SETCLIENTAREAANIMATION) | — | ✔ | não | idem |
| Animação de menus (SPI_SETMENUANIMATION) | — | ✔ | não | idem |
| Efeitos de transparência (HKCU…\Themes\Personalize) | — | ✔ | não | recria/remove exatamente o estado anterior |
| Plano "Alto desempenho" — **só desktop**, se existir | — | ✔ | não | GUID do plano anterior |
| Plano "Equilibrado" — **só notebook** | ✔ | ✔ | não | GUID do plano anterior |
| Recomendações (inicialização, limpeza, Windows Update, SFC/DISM) | ✔ | ✔ | — | nada é alterado |
| Listas: apps da Loja, serviços e tarefas de terceiros | — | ✔ | — | somente leitura |

**Personalizado:** o técnico vê, para cada ajuste, o que muda, benefício,
riscos, se exige administrador e como reverter, e escolhe os números.

## 5. Fluxo de aplicação (Invoke-AGVexaOptimization)

Padrão = simulação. Com `-Aplicar`:
1 permissões → 2 compatibilidade → 3 diagnóstico → 4 estado atual (plano) →
5 backup específico → 6 ponto de restauração (melhor esforço) → 7 exibir
propostas → 8 confirmação (digitar **APLICAR**) → 9 aplicar só o aprovado →
10 verificar cada item (falha = erro, nunca "sucesso") → 11 relatório → 12 reversão disponível.

Idempotente: o que já está no valor desejado aparece como `JA_APLICADO` e não é reaplicado.

## 6. Interpretar os resultados

| Status | Significado |
|---|---|
| PROPOSTO | será alterado se você confirmar |
| JA_APLICADO | já está no valor desejado |
| NAO_APLICAVEL | não se aplica (ex.: plano de desktop num notebook; requer admin) |
| RECOMENDACAO | ação manual para o técnico |
| ERRO | não foi possível ler; nada será feito com esse item |
| APLICADO_E_VERIFICADO | alterado e conferido |
| FALHOU | não alterado ou não conferido — veja o detalhe |

Inicialização — categorias (heurística por nome, **só orienta**): *Segurança — NÃO desabilitar*,
*Driver/hardware — manter*, *Sincronização/backup — confirmar com o cliente*,
*Opcional — candidato a desabilitar (com o cliente)*, *Revisar com o cliente*.
Desabilitar é sempre manual: Gerenciador de Tarefas > Aplicativos de inicialização
ou Configurações > Aplicativos > Inicialização.

## 7. Medir desempenho antes e depois (comparável)

1. Notebook **na tomada**; Windows Update concluído; reinicie.
2. Aguarde 5 minutos após o login (tarefas pós-inicialização).
3. Meça: tempo de inicialização (cronômetro: botão → área de trabalho utilizável),
   abertura de um programa padrão, uso de RAM/CPU em repouso (Gerenciador de Tarefas).
4. Aplique os ajustes, reinicie, repita **nas mesmas condições**, 3 vezes, use a média.
5. Registre em `testes-finais.md`. Não prometa números ao cliente.

## 8. Reverter

Menu 7, ou:
```powershell
.\Restore-AGVexaSettings.ps1 -Listar
.\Restore-AGVexaSettings.ps1 -Sessao ultima          # pede para digitar RESTAURAR
.\Restore-AGVexaSettings.ps1 -Sessao <nome> -WhatIf  # só mostra
```
Backups ficam no próprio computador: `C:\ProgramData\AGVexa\Optimizer\sessoes\`.
Não contêm dados pessoais. Podem ser apagados quando o cliente não precisar mais da reversão.

Privacidade: nome do computador, usuário, número de série e chave do produto
**não** são registrados (exceto com `-IncluirIdentificadores`, mediante autorização).

## 9. Plano de testes em Windows (pendente)

Ambiente: VM Windows 11 e VM Windows 10 (ou PC de laboratório), **não** cliente.

| ID | Teste | Como | Esperado |
|---|---|---|---|
| W-1 | Sintaxe | `.\tests\Invoke-AGVexaSelfTest.ps1 -SyntaxOnly` | 0 falhas |
| W-2 | Autoteste sem privilégios | PowerShell comum: `.\tests\Invoke-AGVexaSelfTest.ps1` | 0 falhas; nada alterado |
| W-3 | Autoteste com privilégios | PowerShell admin, mesmo comando | 0 falhas; Secure Boot/BitLocker/TPM lidos |
| W-4 | Pester | `Invoke-Pester .\tests\AGVexa.Optimizer.Tests.ps1` (Pester 5 no laboratório) | todos passam |
| W-5 | Modo análise | opções 1, 2/3 e responder "não" | nenhum valor muda |
| W-6 | Simulação | `Invoke-AGVexaOptimization.ps1 -Perfil Desempenho` | plano exibido; nada alterado |
| W-7 | WhatIf | `... -Aplicar -WhatIf` | nada alterado |
| W-8 | Aplicar + reverter | `.\tests\Invoke-AGVexaSelfTest.ps1 -CicloReal` (VM) | valores voltam aos originais |
| W-9 | Execução repetida | aplicar 2× | 2ª vez: tudo `JA_APLICADO` |
| W-10 | Erros | executar sem permissão de escrita em ProgramData; catálogo corrompido | mensagem clara, código ≠ 0, nada alterado |
| W-11 | Relatórios | opção 6 | HTML/MD abrem; sem dados pessoais |
| W-12 | Notebook × desktop | VM com bateria simulada ou notebook real | plano de energia correto por tipo |
| W-13 | PowerShell 5.1 e 7 | repetir W-2 em ambos | iguais |

Versões efetivamente testadas: **nenhuma até o momento.** Atualize esta linha após os testes.
