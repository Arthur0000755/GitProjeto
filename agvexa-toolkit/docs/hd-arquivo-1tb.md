# HD de arquivo da empresa (1 TB) — criptografia e organização

Decisão do proprietário (2026-10-15):

| HD | Função | Onde fica |
|---|---|---|
| **320 GB** | HD do toolkit (Ventoy, ISOs, DRIVERS, INSTALADORES, FERRAMENTAS, BIOS_FIRMWARE, AGVexa) | vai aos atendimentos |
| **1 TB** | arquivo da AG Vexa: documentos da empresa, cópia mestre do toolkit, backups de clientes | fica na bancada; sai só quando necessário |

Este guia transforma o HD de 1 TB, que **já tem dados da empresa**, num arquivo
criptografado e organizado **sem perder o conteúdo**. Nada aqui é executado por
scripts do projeto: são passos manuais no Windows.

> Regra de ouro: **antes de criptografar, tenha uma cópia de tudo em outro lugar.**
> A criptografia em disco com dados é segura quando concluída, mas uma queda de
> energia, um desligamento do cabo USB ou um setor ruim no meio do processo podem
> deixar o disco ilegível.

## Etapa 1 — Saúde do disco (somente leitura)

1. Conecte o HD de 1 TB num computador Windows.
2. Rode o CrystalDiskInfo (versão portátil, site oficial) ou, pelo toolkit, `smartctl -a` no SystemRescue.
3. Anote: estado geral, *Reallocated Sectors*, *Current Pending Sectors*, *Uncorrectable*, horas ligadas.
4. Qualquer setor realocado/pendente crescendo → **não criptografe este disco**; copie os dados
   para um disco novo e use o disco novo como arquivo.

Faça o mesmo com o HD de **320 GB** antes de instalar o Ventoy nele.

## Etapa 2 — Cópia de segurança antes de mexer

1. Liste o que existe no 1 TB e quanto ocupa (Propriedades da unidade).
2. Copie **tudo** para outro meio com espaço suficiente (o servidor, outro disco, nuvem
   criptografada). Para muitos arquivos, no Prompt de Comando:
   ```bat
   robocopy E:\ D:\COPIA-HD1TB /E /COPY:DAT /R:1 /W:1 /LOG:D:\copia-hd1tb.log
   ```
   (troque `E:` pela letra do HD de 1 TB e `D:\COPIA-HD1TB` pelo destino). O `robocopy`
   **só copia**; nada é apagado da origem.
3. Confira: compare quantidade de arquivos e tamanho total; abra alguns arquivos importantes.

## Etapa 3 — Escolher a criptografia

| Opção | Requisito | Prós | Contras |
|---|---|---|---|
| **BitLocker To Go** (recomendado se houver Windows Pro) | ativar: Windows 10/11 **Pro**; abrir: qualquer Windows 10/11 | nativo, simples, criptografa com o disco em uso, sem formatar | não abre em Linux/macOS sem programas extras |
| **VeraCrypt** | instalar o VeraCrypt (gratuito, site oficial) em cada PC que for abrir o disco | funciona em Windows Home, Linux e macOS | precisa do programa; criptografia "no lugar" exige partição NTFS e é mais lenta |

Se o HD de 1 TB estiver em **exFAT ou FAT32**, o BitLocker funciona; o VeraCrypt "no lugar" não
(seria preciso copiar tudo, formatar e copiar de volta — por isso a Etapa 2 é obrigatória).

## Etapa 4A — BitLocker To Go (sem formatar)

1. Explorador de Arquivos → botão direito no HD de 1 TB → **Ativar BitLocker**.
2. Escolha **Usar uma senha** (mínimo 8 caracteres; use uma frase longa).
3. **Salve a chave de recuperação** em arquivo **fora** do HD (pen drive guardado à parte e/ou
   cofre de senhas da empresa). Imprima uma cópia e guarde em local seguro.
4. Escolha **Criptografar a unidade inteira** (o disco já foi usado: espaço "livre" pode
   conter restos de arquivos apagados).
5. Modo: **Modo compatível** (para abrir também em outros Windows).
6. Inicie. **Não desconecte** o HD até terminar (pode levar horas em 1 TB via USB 2.0).
   Pode usar o PC normalmente; se precisar parar, use *Pausar* no painel do BitLocker.

## Etapa 4B — VeraCrypt (alternativa)

1. Instale o VeraCrypt do site oficial e confira a assinatura/hash publicados.
2. *Create Volume* → *Encrypt a non-system partition/drive* → *Standard* → selecione a partição
   do HD de 1 TB → *Encrypt partition in place* (só NTFS) → algoritmo padrão (AES) → senha longa.
3. Faça o **backup do cabeçalho do volume** (*Tools → Backup Volume Header*) e guarde fora do HD.
4. Não desconecte até terminar.

## Etapa 5 — Organização dentro do HD

```
EMPRESA/              documentos administrativos da AG Vexa
TOOLKIT-MESTRE/       cópia mestre do que vai para o HD de 320 GB
  isos/               ISOs + arquivos de checksums oficiais
  extras/             DRIVERS, INSTALADORES, FERRAMENTAS, BIOS_FIRMWARE
BACKUPS-CLIENTES/
  OS-2026-0001/       uma pasta por ordem de serviço, nunca o nome do cliente
    LEIA-ME.txt       data de entrada, prazo de guarda, data prevista de exclusão
RELATORIOS/           relatórios de atendimento (cópias locais)
```

Regras:

- Backups de clientes: **prazo de guarda combinado** (ex.: 30 dias após a entrega); depois,
  excluir e registrar a exclusão no `entrega-equipamento.md`.
- Nunca guardar senhas, documentos pessoais ou fotos além do necessário ao serviço.
- O HD fica **na bancada**, desconectado quando não estiver em uso. Não levar a atendimentos.

## Etapa 6 — Uma segunda cópia (o 1 TB não pode ser o único lugar)

Os documentos da empresa e a cópia mestre do toolkit precisam existir em **pelo menos dois
lugares** (regra 3-2-1: 3 cópias, 2 mídias, 1 fora do local). Opções: o servidor da AG Vexa,
outro disco, ou nuvem com criptografia própria. Backups de clientes **não** vão para a nuvem
sem autorização e criptografia.

## Etapa 7 — Rotina mensal

- [ ] SMART dos dois HDs (320 GB e 1 TB): valores iguais ou melhores que o mês anterior.
- [ ] Apagar backups de clientes vencidos e registrar.
- [ ] Atualizar a segunda cópia dos documentos da empresa.
- [ ] Testar se a chave de recuperação/cabeçalho guardados ainda estão acessíveis.
