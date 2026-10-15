# Riscos e limitações

## 1. Limitações conhecidas (0.1.0-rc1)

| # | Limitação | Impacto | Mitigação |
|---|---|---|---|
| L1 | Nenhum teste de boot real (VM ou físico) foi executado | não se sabe ainda se o tema/menu renderizam como planejado | plano em `plano-de-testes-boot.md`; homologação acompanhada |
| L2 | Documentação web do Ventoy inacessível no ambiente de desenvolvimento | confirmação feita no código-fonte 1.1.18 (implementação real); comportamento de versões futuras pode mudar | validar com `F5 > verificar plugin` no boot; reconferir ao atualizar o Ventoy |
| L3 | Pré-visualizações do tema são **aproximadas** (Pillow) | posição/fonte reais podem diferir um pouco | ajustar após VM-1/HW |
| L4 | Fonte do menu é a bitmap padrão do Ventoy (16 px) | texto pequeno em telas grandes | gfxmode 1024×768; fontes `.pf2` próprias exigem `grub-mkfont` (não instalado) |
| L5 | "07 — Informações do Toolkit" não pode ser item do menu principal | Ventoy só lista imagens/pastas | implementado no F6; indicado no painel "Como usar" |
| L6 | Modo texto (CLI) não mostra acentos | nomes com "ç/ã" ficam estranhos | `--ascii-menu` no staging |
| L7 | Nenhuma ISO real foi baixada | catálogo sem SHA‑256 preenchido | processo em `ferramentas.md` |
| L8 | Windows Optimizer não executado em Windows | nenhuma validação funcional | autoteste e Pester prontos para o laboratório |
| L10 | QEMU/OVMF/pwsh/shellcheck ausentes no ambiente | testes correspondentes "Não testado" | instalar só com autorização |
| L11 | Desenvolvimento feito em contêiner de nuvem (Ubuntu 24.04), não no servidor Ubuntu 26.04 | ambiente diferente do alvo | `scripts/preflight.sh` no servidor antes de usar |

## 2. Riscos operacionais (uso em clientes)

| Risco | Probabilidade | Gravidade | Controle |
|---|---|---|---|
| Gravar no disco errado (formatação, clone invertido) | média | **crítica** | identificação por modelo/série/tamanho; dicas no menu; checklists; regra "origem/destino em voz alta" |
| Disco degradado piorar durante o uso | média | alta | SMART antes; ddrescue para imagem; não gravar no disco suspeito |
| ISO adulterada/corrompida | baixa | alta | SHA‑256 oficial obrigatório; DIVERGENTE nunca entra no staging |
| Desativar proteção do firmware (Secure Boot) e esquecer de reativar | média | média | política "seguir firmware"; checklist pós-instalação pede reativar |
| Contornar requisitos do Windows 11 | baixa | média | `VTOY_WIN11_BYPASS_*=0`; validador recusa `1` |
| Dados pessoais de clientes em relatórios/mídia | média | alta | relatórios sem identificadores por padrão; prazo de guarda e exclusão no checklist de entrega |
| Boot automático indesejado | baixa | alta | sem timeout/imagem padrão; validador recusa |
| Otimização mal aplicada no Windows | baixa | média | padrão análise; backup; confirmação digitada; reversão verificada |
| HD do toolkit perdido/roubado | baixa | média | sem pasta CLIENTES na mídia (staging e validador recusam); dados de clientes só em disco/partição criptografada separada, por prazo curto |

## 3. Riscos do projeto / terceiros

- **Ventoy**: projeto mantido por um autor principal; o projeto publica `BLOB_List.md`
  com instruções de compilação dos binários pré-compilados. Acompanhar releases e notas de segurança.
- **Secure Boot do Ventoy**: depende de shim de terceiros (o próprio código informa shim da Rocky Linux).
  Revogações de certificados (DBX/SBAT) por atualizações de firmware podem impedir o boot com Secure Boot ativo no futuro.
- **Ferramentas**: mudanças de versão podem alterar compatibilidade com Ventoy; testar a cada atualização.
