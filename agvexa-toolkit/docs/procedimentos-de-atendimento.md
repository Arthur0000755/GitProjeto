# Procedimentos de atendimento — AG Vexa

Cada procedimento segue: **Sintoma → Hipóteses → Testes (evidências) → Conclusão → Ação autorizada → Registro.**
Use os modelos de `templates/relatorios/` (`scripts/novo-relatorio.sh --listar`).

Regra comum a todos: **autorização do proprietário antes de qualquer ação que grave dados.**

---

## P1. Computador que não inicia

**Sintoma:** não liga, liga sem imagem, ou liga e não carrega o sistema.

| Fase | Passos |
|---|---|
| Separar o problema | (a) Não liga: fonte/carregador, tomada, botão. (b) Liga sem imagem: monitor/cabo, RAM, vídeo. (c) Mostra logo/erro: armazenamento ou sistema. |
| Hipóteses (caso c) | disco com defeito; sistema corrompido; boot apagado; ordem de boot errada |
| Evidências | 1) BIOS/UEFI reconhece o disco? 2) Boot pelo toolkit funciona? (prova que placa/RAM/vídeo respondem) 3) SMART (SystemRescue). 4) MemTest86+ se houver travamentos. 5) Partições visíveis (GParted, só olhar). |
| Conclusão | ex.: "Disco OK, partições presentes, Windows não inicia → corrupção do sistema provável" |
| Ação autorizada | 1º copiar dados (SystemRescue/Ubuntu Live, montagem só leitura) → 2º reparo do Windows (mídia oficial > Reparar) → 3º reinstalação só com P5 e autorização |
| Registro | `diagnostico-inicial.md` |

## P2. Notebook com lentidão

| Fase | Passos |
|---|---|
| Hipóteses | disco (HD mecânico lento ou degradado); pouca RAM; muitos programas ao iniciar; superaquecimento/poeira; atualizações em andamento; malware |
| Evidências | SMART do disco; RAM total e uso (Gerenciador de Tarefas); temperatura/ruído do cooler; tempo de inicialização cronometrado; `Get-AGVexaSystemInfo` (Optimizer opção 1); lista de inicialização (opção 5) |
| Cuidados | compare medições **nas mesmas condições**: na tomada, após atualizações e reinício, sem programas abertos |
| Conclusão | ex.: "HD mecânico saudável, 4 GB RAM, 14 itens na inicialização → recomenda-se SSD; revisão de inicialização" |
| Ação autorizada | limpeza física; revisão de inicialização **com o cliente**; Optimizer perfil Conservador/Desempenho; upgrade de SSD/RAM com orçamento aprovado |
| Registro | `checklist-manutencao.md` + relatório do Optimizer |

## P3. Suspeita de HD ou SSD defeituoso

1. **Pare de gravar no disco.** Não instale programas de "reparo" no Windows do cliente.
2. Boot pelo toolkit → SystemRescue → `lsblk` → `smartctl -H` e `smartctl -a`.
3. Interprete (Manual 3.4). Ruído de batida → desligue e encaminhe a laboratório.
4. Se houver dados importantes e sinais de degradação: **ddrescue** para outro disco (Manual 3.10).
5. Só depois: teste longo (`smartctl -t long`) se o cliente quiser confirmação e o disco aguentar.
6. Conclusão com evidência numérica (atributos 5/197/198, autoteste).
7. Registro: modelo, série, valores, recomendação (troca), dados salvos.

## P4. Teste de memória RAM

1. Hipótese: travamentos/telas azuis aleatórias; erros ao instalar.
2. Boot → 02 → MemTest86+ → ao menos 1 passada completa.
3. Com erro: teste 1 pente por vez, no mesmo slot; depois troque de slot para separar pente × slot.
4. Conclusão: "módulo X com erros", "slot Y com falha" ou "sem erros em N passadas (não exclui outras causas)".
5. Registro: passadas, erros, configuração testada.

## P5. Backup antes da formatação

1. Preencha `checklist-pre-formatacao.md` (itens ★ obrigatórios).
2. Se o Windows inicia: copie as pastas do usuário para o disco de destino.
3. Se não inicia: Ubuntu Live ou SystemRescue, monte a partição do Windows **somente leitura** e copie.
4. Disco com SMART ruim: use ddrescue antes (P3).
5. Backup completo opcional: imagem com Rescuezilla (Manual 3.5).
6. **Confira o backup** (abrir arquivos, comparar tamanhos) **com o cliente quando possível**.
7. Só então siga para P6.

## P6. Reinstalação autorizada do sistema operacional

1. Autorização escrita + P5 concluído.
2. ISO com status VERIFICADA; edição compatível com a licença.
3. Instalação (Manual 3.1), excluindo partições **apenas** do disco combinado.
4. Pós-instalação: `checklist-pos-instalacao.md` (Windows Update, drivers oficiais, segurança).
5. Optimizer: diagnóstico (opção 1) → perfil escolhido com o cliente → relatório (opção 6).
6. Restaure os dados e confira com o cliente.
7. `testes-finais.md` e `entrega-equipamento.md`.

## P7. Recuperação de arquivos apagados

1. **Pare de usar o disco/cartão imediatamente** (cada gravação pode sobrescrever o arquivo).
2. Explique ao cliente: não há garantia; nomes podem se perder.
3. Disco com sinais de defeito → ddrescue primeiro (P3) e trabalhe na imagem.
4. Partição perdida → TestDisk (listar e copiar arquivos). Arquivos apagados → PhotoRec.
5. Destino: **sempre outro disco**.
6. Verifique amostras com o cliente; entregue em mídia combinada.
7. Registre tipos, quantidade e o que não foi possível recuperar.

## P8. Verificação de conectividade

1. Confirme que a rede é do cliente e que há autorização.
2. Teste no Windows; depois, pelo toolkit (Ubuntu Live/SystemRescue) — Manual 3.11.
3. Conclusões típicas:
   - Live conecta, Windows não → driver/configuração do Windows.
   - Nenhum conecta por cabo e "Link detected: no" → cabo/porta/switch.
   - IP ok, gateway responde, internet não → roteador/provedor.
   - Ping por IP ok, por nome não → DNS.
4. Registre cada etapa e o resultado.
