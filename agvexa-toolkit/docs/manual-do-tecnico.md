# Manual do Técnico — AG Vexa Toolkit

Para quem está começando na assistência técnica (curso Técnico em Informática).
Leia uma vez inteiro; depois use como consulta. Procedimentos completos de
atendimento estão em `procedimentos-de-atendimento.md`.

---

## Parte 1 — Princípios

### 1.1 Diagnóstico, hipótese, evidência e conclusão

| Termo | O que é | Exemplo |
|---|---|---|
| **Sintoma** | o que o cliente relata ou você observa | "o notebook está lento" |
| **Hipótese** | uma causa possível, ainda não comprovada | disco com defeito; pouca RAM; muitos programas ao iniciar; superaquecimento |
| **Evidência** | resultado de um teste, com ferramenta e valor | SMART: 120 setores pendentes (atributo 197) |
| **Conclusão** | o que as evidências sustentam, com grau de certeza | "Disco em degradação; lentidão compatível com releituras de setores" |

Regras de ouro:

1. **Um sintoma isolado nunca é diagnóstico.** "Lento" tem dezenas de causas.
2. Toda conclusão precisa de **pelo menos uma evidência registrada**.
3. Teste uma hipótese de cada vez; anote também os testes que deram **normal**.
4. Se as evidências não fecham, a conclusão é "inconclusivo" — e isso é honesto.

### 1.2 Clonar × imagem × recuperar arquivos × reparar partições

| Operação | O que faz | Quando | Risco principal |
|---|---|---|---|
| **Clonar** | copia um disco **direto** para outro disco | trocar HD por SSD; migrar sistema | destino é **sobrescrito**; inverter origem/destino destrói os dados |
| **Imagem** | salva o disco em **arquivos** em outro disco | backup completo antes de formatar/reparar | destino sem espaço; imagem não conferida |
| **Recuperar arquivos** | lê dados apagados/perdidos e salva em **outro** disco | arquivos apagados, partição formatada por engano | salvar no mesmo disco sobrescreve o que restava |
| **Reparar partições** | grava tabela de partições/setor de boot | partição "sumiu", disco aparece como não alocado | gravação errada piora o caso — **sempre depois do backup/imagem** |

Ordem segura em casos de dados importantes: **imagem (ou ddrescue) → trabalhar na cópia → reparar o original só se necessário.**

### 1.3 Regras de segurança do toolkit

- Autorização do proprietário **por escrito** antes de qualquer gravação.
- Backup **conferido** antes de reparar, formatar ou instalar.
- Identifique discos por **modelo, número de série e capacidade** — nunca só pela letra (`sda`, `Disco 0`).
- Disco com ruído, lentidão extrema ou SMART ruim: **não grave nele**; priorize copiar os dados.
- Não contorne senhas, BitLocker ou outra criptografia.
- Não copie dados pessoais sem autorização; nada é enviado para a internet.
- Use só ISOs **VERIFICADAS** (status no menu e no relatório do `verify-isos.sh`).

---

## Parte 2 — Usando o HD do toolkit

1. Conecte o HD, ligue o computador e abra o menu de boot do firmware
   (F12, F11, F10, F9, F8 ou Esc, conforme o fabricante).
2. Prefira a entrada **UEFI** do HD. Use "Legacy/CSM" só em máquinas antigas.
3. No menu AG Vexa: setas para navegar, **Enter** abre a categoria/inicia, **Esc** volta.
4. A dica abaixo do menu explica cada categoria e ferramenta.
5. **F6**: informações do toolkit, regras de segurança, identificação rápida do computador, reiniciar/desligar.
6. **F5**: ferramentas do Ventoy — trocar tema (*Seleção de Tema* → AG Vexa leve), resolução, **modo texto** se a tela falhar, informações de hardware.
7. **F4**: iniciar o sistema instalado no computador (sem usar o toolkit).

Se aparecer o **MokManager** (tela azul) com Secure Boot ativo, leia `compatibilidade.md` antes de prosseguir: registrar chaves altera o firmware do cliente.

---

## Parte 3 — Ferramentas

Cada ferramenta segue o mesmo roteiro: **(1) o que é · (2) para que serve · (3) quando usar · (4) quando não usar · (5) riscos · (6) pré-requisitos · (7) procedimento básico · (8) cuidados antes · (9) como verificar o resultado · (10) como registrar.**

### 3.1 Instalador do Windows 11 / Windows 10

1. **O que é:** mídia oficial de instalação da Microsoft.
2. **Para que serve:** instalação limpa ou reinstalação do Windows.
3. **Quando usar:** sistema corrompido sem reparo viável; troca de disco; pedido do cliente — sempre com autorização.
4. **Quando não usar:** sem backup conferido; sem licença do cliente; disco com SMART ruim (troque o disco primeiro). Windows 10: só com justificativa registrada (fim do suporte regular em 14/10/2025).
5. **Riscos:** apagar a partição/disco errado; perder dados não copiados; edição errada (Home × Pro) impede a ativação.
6. **Pré-requisitos:** `checklist-pre-formatacao.md` completo; ISO com status VERIFICADA; equipamento na tomada.
7. **Procedimento básico:** boot UEFI pelo HD → categoria 01 → Windows 11 → idioma → "Não tenho chave" se a ativação for digital → **Personalizada** → na tela de discos, identifique o disco pelo **tamanho** → excluir só as partições do disco de destino combinado → instalar.
8. **Cuidados antes:** desconecte discos de dados extras quando possível; anote a chave de recuperação do BitLocker se existir.
9. **Verificar:** Windows inicia; Ativação em Configurações > Sistema > Ativação; Gerenciador de Dispositivos sem alertas.
10. **Registrar:** edição/versão instalada, disco usado, estado da ativação, no `checklist-pos-instalacao.md`.

### 3.2 MemTest86+ (teste de memória RAM)

1. **O que é:** programa livre (GPL) que testa a memória fora do sistema operacional.
2. **Para que serve:** identificar módulos de RAM com defeito.
3. **Quando usar:** telas azuis aleatórias, travamentos, reinícios, corrupção de arquivos, falha ao instalar o sistema.
4. **Quando não usar:** equipamento superaquecendo (resolva a ventilação antes); quando o problema é claramente outro e já comprovado.
5. **Riscos:** baixos (não grava em discos); aquecimento em teste longo.
6. **Pré-requisitos:** equipamento na tomada; ventilação ok; tempo disponível (1 passada pode levar de 30 min a várias horas).
7. **Procedimento:** categoria 02 → MemTest86+ → o teste começa sozinho → aguarde ao menos **1 passada completa** ("Pass: 1"). Para isolar defeito: um pente por vez, mesmo slot.
8. **Cuidados:** não conclua "RAM boa" com teste interrompido no início.
9. **Verificar:** "Errors: 0" ao fim da passada = nenhum erro detectado **naquele teste**; qualquer erro = memória (ou slot/controlador) com problema.
10. **Registrar:** passadas concluídas, erros, módulos/slots testados, tempo, temperatura percebida.

### 3.3 GParted Live (partições)

1. **O que é:** sistema live com o editor de partições GParted.
2. **Para que serve:** ver o layout dos discos; quando autorizado, criar/redimensionar/mover/formatar partições; checar sistemas de arquivos.
3. **Quando usar:** entender a estrutura de um disco; preparar disco novo; redimensionar com backup feito.
4. **Quando não usar:** disco com suspeita de defeito físico; sem backup; para "recuperar" partição perdida (use TestDisk sobre uma cópia).
5. **Riscos:** **altos** ao aplicar operações: perda total de dados, sistema que não inicia.
6. **Pré-requisitos:** backup conferido; disco identificado por modelo/série; energia estável (no notebook, na tomada).
7. **Procedimento:** categoria 03 → GParted Live → aceite o padrão de teclado/idioma → no canto superior direito selecione o disco → **observe** antes de qualquer coisa → só então enfileire operações → revise a lista → "Aplicar".
8. **Cuidados:** as operações só acontecem ao clicar em **Aplicar** (botão ✓). Revise a fila. Nunca interrompa um redimensionamento.
9. **Verificar:** layout final na tela; o sistema do cliente inicia (se aplicável).
10. **Registrar:** capturas/anotações do layout **antes e depois**, operações aplicadas.

### 3.4 SMART: smartctl e GSmartControl

1. **O que é:** leitura dos indicadores de saúde que o próprio disco registra (SMART).
2. **Para que serve:** evidência objetiva de degradação de HD/SSD.
3. **Quando usar:** lentidão, travamentos ao acessar arquivos, ruídos, antes de formatar/clonar, antes de recuperar dados.
4. **Quando não usar:** como única evidência de "disco bom" — SMART normal **não garante** ausência de defeito.
5. **Riscos:** leitura é segura. Autoteste longo (`-t long`) é seguro para os dados, mas força um disco já fraco.
6. **Pré-requisitos:** SystemRescue (categoria 05) ou outro live com smartmontools.
7. **Procedimento (terminal, somente leitura):**
   ```bash
   lsblk -d -o NAME,MODEL,SERIAL,SIZE,TRAN     # identificar o disco
   sudo smartctl -H /dev/sdX                   # avaliação geral
   sudo smartctl -a /dev/sdX                   # todos os atributos (HD/SSD SATA)
   sudo smartctl -a /dev/nvme0                 # SSD NVMe
   sudo smartctl -a -d sat /dev/sdX            # disco em gaveta USB, se o comando acima falhar
   sudo smartctl -t short /dev/sdX             # autoteste curto (~2 min), depois:
   sudo smartctl -l selftest /dev/sdX
   ```
8. **Cuidados:** confira o modelo/série na saída antes de concluir sobre o disco certo.
9. **Verificar — pontos de atenção:**
   - 5 *Reallocated_Sector_Ct*, 197 *Current_Pending_Sector*, 198 *Offline_Uncorrectable*: acima de 0 e crescendo → degradação.
   - 199 *UDMA_CRC_Error_Count* crescendo → muitas vezes **cabo/conector**, não o disco.
   - NVMe: *Critical Warning* ≠ 0, *Media and Data Integrity Errors* > 0, *Percentage Used* perto de 100 %.
   - Autoteste com "read failure" → disco com defeito.
10. **Registrar:** modelo, série, horas ligadas, valores dos atributos acima, resultado do autoteste.

### 3.5 Rescuezilla (backup, restauração e clonagem com interface gráfica)

1. **O que é:** ferramenta livre (GPL‑3.0) com interface gráfica; compatível com imagens do Clonezilla.
2. **Para que serve:** criar **imagem** de um disco inteiro, restaurar, clonar disco para disco.
3. **Quando usar:** backup completo antes de formatar ou reparar; migração HD → SSD.
4. **Quando não usar:** disco com defeito físico grave (prefira ddrescue); destino menor que o necessário.
5. **Riscos:** restaurar/clonar **sobrescreve** o destino.
6. **Pré-requisitos:** disco de destino com espaço suficiente; origem e destino identificados por modelo/série/tamanho.
7. **Procedimento (backup):** categoria 04 → Rescuezilla → *Backup* → selecione **origem** → selecione **destino** (outro disco) → pasta → confirme → aguarde.
8. **Cuidados:** a tela de resumo mostra origem e destino — leia antes de confirmar.
9. **Verificar:** mensagem de sucesso; a pasta da imagem existe no destino; quando oferecido, use a verificação da imagem.
10. **Registrar:** origem, destino, tamanho, duração, local da imagem e prazo de guarda.

### 3.6 Clonezilla Live (avançado)

1. **O que é:** ferramenta livre (GPL) de clonagem/imagem em modo texto.
2. **Para que serve:** o mesmo que o Rescuezilla, com mais opções (rede, modos avançados).
3. **Quando usar:** quando o Rescuezilla não atender e você tiver prática.
4. **Quando não usar:** se você não entende cada tela. Prefira o Rescuezilla.
5. **Riscos:** muito altos se origem e destino forem invertidos.
6. **Pré-requisitos:** os mesmos do Rescuezilla; tempo para ler cada tela.
7. **Procedimento:** categoria 06 → Clonezilla → modo *Beginner* → *device-image* (imagem) ou *device-device* (clone) → siga as telas.
8. **Cuidados:** o Clonezilla pede confirmação dupla — leia o nome do disco nas duas.
9. **Verificar:** mensagens finais sem erro; opção de checar a imagem.
10. **Registrar:** como no Rescuezilla.

### 3.7 SystemRescue (ambiente de resgate)

1. **O que é:** sistema live de manutenção com dezenas de ferramentas.
2. **Para que serve:** SMART, TestDisk, PhotoRec, ddrescue, GParted, rede, acesso a arquivos.
3. **Quando usar:** diagnóstico de discos, cópia de dados de sistema que não inicia, recuperação.
4. **Quando não usar:** para tarefas que o técnico não domina em linha de comando sem procedimento escrito.
5. **Riscos:** acesso total aos discos; comandos como `dd`, `mkfs`, `fdisk`, `wipefs` **destroem dados**.
6. **Pré-requisitos:** saber identificar discos (`lsblk`).
7. **Procedimento:** categoria 05 → SystemRescue → opção padrão → `startx` para interface gráfica (quando disponível na versão).
8. **Cuidados:** monte discos do cliente **somente leitura** quando só for copiar: `sudo mount -o ro /dev/sdX2 /mnt`.
9. **Verificar:** dados copiados abrem no destino.
10. **Registrar:** comandos usados e resultados (copie a saída para um arquivo no disco de destino).

### 3.8 TestDisk (partições perdidas)

1. **O que é:** utilitário livre (GPL) da CGSecurity, incluído no SystemRescue.
2. **Para que serve:** encontrar partições perdidas, listar e copiar arquivos delas, reconstruir tabela de partições.
3. **Quando usar:** partição "sumiu", disco aparece "não alocado/RAW".
4. **Quando não usar:** disco com defeito físico (faça ddrescue primeiro e trabalhe na cópia).
5. **Riscos:** a opção **Write** grava uma nova tabela de partições — se errada, piora o caso.
6. **Pré-requisitos:** backup/imagem do disco, de preferência.
7. **Procedimento:** `sudo testdisk` → *Create* (log) → escolha o disco → tipo de tabela (o detectado) → *Analyse* → *Quick Search* → selecione a partição → **P** lista arquivos → **C** copia arquivos para **outro** disco.
8. **Cuidados:** prefira **copiar os arquivos** a gravar a tabela. Use *Write* só com backup e certeza.
9. **Verificar:** arquivos copiados abrem; se gravou a tabela, a partição monta.
10. **Registrar:** partições encontradas, ação tomada, `testdisk.log`.

### 3.9 PhotoRec (arquivos apagados)

1. **O que é:** utilitário livre (GPL) que recupera arquivos pela assinatura do conteúdo.
2. **Para que serve:** recuperar fotos, documentos e outros arquivos apagados ou de partição formatada.
3. **Quando usar:** arquivos apagados; cartão de memória/pen drive formatado.
4. **Quando não usar:** quando o TestDisk consegue listar os arquivos com nomes (é melhor).
5. **Riscos:** salvar no **mesmo** disco sobrescreve os dados; disco com defeito piora com leitura longa.
6. **Pré-requisitos:** disco de destino separado com bastante espaço; cliente ciente de que nomes de arquivos normalmente **não** são recuperados.
7. **Procedimento:** `sudo photorec` → escolha o disco → partição → tipo de sistema de arquivos → *Free* (só espaço livre) ou *Whole* → escolha a pasta de destino **em outro disco** → aguarde.
8. **Cuidados:** use *File Opt* para limitar tipos (ex.: jpg, docx, pdf) e acelerar.
9. **Verificar:** abra amostras dos arquivos recuperados; muitos podem estar incompletos.
10. **Registrar:** tipos buscados, quantidade recuperada, local de entrega ao cliente.

### 3.10 GNU ddrescue (disco com defeito)

1. **O que é:** copiador de discos livre (GPL) feito para mídias com erros de leitura.
2. **Para que serve:** salvar o máximo de dados de um disco degradado para outro disco ou para um arquivo de imagem.
3. **Quando usar:** SMART ruim, ruídos, setores ilegíveis — **antes** de qualquer outra tentativa.
4. **Quando não usar:** disco com ruído de batida mecânica intensa (encaminhar para laboratório especializado; cada minuto ligado pode piorar).
5. **Riscos:** **inverter origem e destino destrói o disco do cliente.**
6. **Pré-requisitos:** destino maior ou igual à origem; identificação certa dos dois discos.
7. **Procedimento (para arquivo de imagem, o mais seguro):**
   ```bash
   lsblk -d -o NAME,MODEL,SERIAL,SIZE         # anote ORIGEM (cliente) e DESTINO
   sudo mount /dev/sdDEST1 /mnt               # partição do disco de destino
   sudo ddrescue -n /dev/sdORIGEM /mnt/cliente.img /mnt/cliente.map    # 1ª passada, rápida
   sudo ddrescue -d -r3 /dev/sdORIGEM /mnt/cliente.img /mnt/cliente.map # novas tentativas
   ```
   Depois, trabalhe (TestDisk/PhotoRec/montagem) **na imagem**, nunca no disco original.
8. **Cuidados:** a ordem é sempre `ddrescue ORIGEM DESTINO MAPA`. Leia a linha duas vezes antes do Enter. O arquivo de mapa permite continuar de onde parou.
9. **Verificar:** ao final, o ddrescue mostra "rescued" (recuperado) e "bad areas"; percentual próximo de 100 % indica boa cópia.
10. **Registrar:** percentual recuperado, áreas ruins, tempo, local da imagem.

### 3.11 Diagnóstico de rede (autorizado)

1. **O que é:** comandos de rede presentes no SystemRescue e no Ubuntu Live.
2. **Para que serve:** separar problema do **computador** de problema da **rede/provedor**.
3. **Quando usar:** "a internet não funciona" só neste equipamento; antes de reinstalar por "problema de rede".
4. **Quando não usar:** em redes de terceiros sem autorização; nunca para varrer, capturar tráfego ou testar senhas.
5. **Riscos:** baixos com os comandos abaixo (só leitura/teste de conectividade).
6. **Pré-requisitos:** rede do cliente e autorização para conectar.
7. **Procedimento (do mais próximo ao mais distante):**
   ```bash
   ip -br link                  # interface existe? UP?
   ip -br addr                  # recebeu endereço IP?
   ip route                     # qual é o gateway (roteador)?
   ping -c 4 <gateway>          # chega ao roteador?
   ping -c 4 1.1.1.1            # chega à internet por IP?
   ping -c 4 www.google.com     # o DNS resolve nomes?
   tracepath 1.1.1.1            # onde a rota para (se parar)
   dig www.google.com           # ou: nslookup www.google.com
   sudo ethtool <interface>     # cabo: velocidade e "Link detected"
   ```
8. **Cuidados:** a disponibilidade exata de cada comando varia por versão da ferramenta live.
9. **Verificar:** live funciona e o Windows não → problema no Windows/driver; nenhum funciona → rede/cabo/roteador/provedor.
10. **Registrar:** resultado de cada etapa (ok/falha) e a conclusão.

### 3.12 Ubuntu Desktop Live

1. **O que é:** sistema Linux completo que roda do HD sem instalar.
2. **Para que serve:** testar hardware (vídeo, som, Wi-Fi, webcam), copiar arquivos com interface amigável, navegar.
3. **Quando usar:** confirmar se um problema é de hardware ou do Windows; resgate simples de arquivos.
4. **Quando não usar:** para instalar o Ubuntu sem pedido do cliente.
5. **Riscos:** a opção **Instalar** pode apagar o disco.
6. **Pré-requisitos:** nenhum além do boot.
7. **Procedimento:** categoria 05 → Ubuntu → *Experimentar/Try Ubuntu*.
8. **Cuidados:** ao abrir discos do cliente, apenas copie; não exclua nada.
9. **Verificar:** dispositivos funcionando no live = hardware provavelmente bom.
10. **Registrar:** o que funcionou e o que não funcionou no live.

### 3.13 AG Vexa Windows Optimizer (pós-formatação)

Resumo: scripts PowerShell na pasta `AGVexa/windows-optimizer` do HD. Padrão
é **somente análise**; alterações só com avaliação, backup e confirmação.
Manual completo: `windows-optimizer.md`.

---

## Parte 4 — Quando parar e pedir ajuda

- Disco com batidas/cliques mecânicos.
- Cliente sem backup e dados de alto valor (empresa, fotos insubstituíveis) em disco com SMART ruim.
- Equipamento com BitLocker sem chave de recuperação.
- Qualquer tela em que você não tem certeza de qual é o disco de origem e de destino.

"Não sei, vou confirmar" é uma resposta profissional.
