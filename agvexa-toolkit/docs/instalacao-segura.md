# Instalação segura no HD externo (Fase F — NÃO executada)

> **Este procedimento APAGA o HD escolhido.** Ele está documentado para execução
> futura, **acompanhada pelo proprietário**, com autorização específica.
> Nenhum script do projeto executa estes comandos: todos os passos são manuais.
> Não presuma que dados existentes no HD serão preservados.

Pré-requisitos

- Staging gerado e validado: `scripts/prepare-staging.sh` e
  `scripts/validate-config.sh --staging build/staging` sem erros.
- Pacote **oficial** do Ventoy para Linux (`ventoy-<versão>-linux.tar.gz`),
  com SHA-256 conferido contra o valor publicado na página da release.
- Computador onde o HD será preparado (de preferência **não** o servidor de
  produção: um notebook/desktop de bancada evita qualquer risco aos serviços).
- Pacotes necessários no computador de preparação: os scripts do próprio
  Ventoy usam `parted`/`fdisk`, `mkfs.exfat` (incluído no pacote), `dd`.

## Etapa 1 — Backup do conteúdo atual do HD

1. Conecte o HD e **não** formate nada.
2. Liste o conteúdo e decida com o proprietário o que precisa ser guardado.
3. Copie para outro meio e **confira** (abrir arquivos, comparar tamanhos ou `sha256sum`).
4. Registre no checklist: "backup do HD do toolkit conferido em __/__/__".

## Etapa 2 — Identificação inequívoca do disco

Execute **antes e depois** de conectar o HD e compare as listas:

```bash
lsblk -d -o NAME,MODEL,SERIAL,SIZE,TRAN,RM,TYPE
ls -l /dev/disk/by-id/ | grep -v part
```

Preencha a tabela e confira **três** atributos (nunca só a letra `sdX`):

| Atributo | Valor esperado | Valor lido |
|---|---|---|
| Modelo | (etiqueta do HD) | |
| Número de série | (etiqueta do HD) | |
| Capacidade | ~931 GiB (1 TB) | |
| Barramento | usb | |
| Caminho estável | `/dev/disk/by-id/usb-...` | |

Regras:

- O nome `sdX` **pode mudar** entre conexões. Use o caminho `/dev/disk/by-id/...`
  (o Ventoy2Disk aceita links simbólicos e os resolve).
- Se houver dúvida, **pare**. Desconecte outros discos USB.
- Nunca use um caminho de partição (`sdX1`); o Ventoy exige o disco inteiro.

## Etapa 3 — Desmontar

```bash
# Ver se há partições montadas do HD (pelo by-id resolvido):
lsblk -o NAME,MOUNTPOINTS /dev/disk/by-id/usb-SEU-HD
# Desmontar cada uma que aparecer montada:
udisksctl unmount -b /dev/sdX1     # exemplo; confira o nome
```

## Etapa 4 — Escolhas de instalação

| Opção | Recomendação | Motivo |
|---|---|---|
| Estilo de partição | **MBR** (padrão do Ventoy) | 1 TB < 2 TB (limite do MBR) e máxima compatibilidade com BIOS antigos. Use `-g` (GPT) só se algum equipamento-alvo exigir. |
| Secure Boot | **habilitado** (`-s`, padrão) | permite boot com Secure Boot ativo após registrar a chave (MokManager). |
| Reserva de espaço | não usar no início | `-r <MiB>` reserva espaço no fim do disco; só se for criar partição extra planejada. |
| Instalação "não destrutiva" (`-n`) | **não usar** | recurso de tentativa; o procedimento assume perda total. |
| Rótulo | `-L AGVEXA` | identifica a partição de dados. |

## Etapa 5 — Confirmação explícita (proprietário presente)

Leia em voz alta e marque:

- [ ] O backup da Etapa 1 foi conferido.
- [ ] O disco `/dev/disk/by-id/________` tem modelo, série e capacidade conferidos.
- [ ] Nenhum outro disco USB está conectado.
- [ ] O proprietário autorizou apagar este HD. Assinatura/data: ____________

## Etapa 6 — Instalar o Ventoy (APAGA O HD)

```bash
cd vendor/ventoy-<versão>            # pacote oficial conferido
sudo sh Ventoy2Disk.sh -i -s -L AGVEXA /dev/disk/by-id/usb-SEU-HD
# O script mostra disco, tamanho e estilo e pede confirmação DUAS vezes.
# Confira de novo o disco exibido antes de responder "y".
```

Conferência (somente leitura):

```bash
sudo sh Ventoy2Disk.sh -l /dev/disk/by-id/usb-SEU-HD   # versão, estilo, Secure Boot
lsblk -o NAME,SIZE,FSTYPE,LABEL /dev/disk/by-id/usb-SEU-HD
```

## Etapa 7 — Copiar o staging

O exFAT não aceita links simbólicos: a cópia deve **seguir os links** das ISOs.

```bash
# montar a partição 1 (AGVEXA) pelo gerenciador de arquivos ou:
udisksctl mount -b /dev/disk/by-label/AGVEXA
DEST=/media/$USER/AGVEXA                            # confira o ponto de montagem
cp -rL --preserve=timestamps build/staging/. "$DEST"/   # ou: rsync -rL --progress build/staging/ "$DEST"/
rm -f "$DEST/.agvexa-staging"                       # marcador interno do staging
sync
```

## Etapa 8 — Validar a cópia

```bash
cd "$DEST" && sha256sum -c --quiet SHA256SUMS-AGVEXA.txt && echo "CÓPIA ÍNTEGRA"
```

Qualquer `FAILED` → copie de novo o arquivo indicado. Depois:

```bash
cd ~ && udisksctl unmount -b /dev/disk/by-label/AGVEXA && udisksctl power-off -b /dev/disk/by-id/usb-SEU-HD
```

## Etapa 9 — Primeiro boot e testes físicos

1. Siga `plano-de-testes-boot.md` (UEFI, BIOS, Secure Boot, resoluções).
2. Com Secure Boot ativo, o primeiro boot abre o **MokManager**: escolha
   *Enroll key from disk* → partição VTOYEFI → `ENROLL_THIS_KEY_IN_MOKMANAGER.cer`.
   Faça isso **somente em equipamentos da AG Vexa**. Em equipamento de cliente,
   registrar chaves altera o firmware do cliente: só com autorização explícita
   do cliente; a alternativa é desativar o Secure Boot temporariamente e
   reativá-lo ao final (registrar no relatório).
3. No menu, `F5 > verificar configuração do plugin json` confere o `ventoy.json`
   na própria máquina.
4. Registre os resultados em `relatorio-de-validacao.md`.

## Atualizações futuras

- Atualizar só arquivos: gere novo staging e copie de novo (Etapas 7–8).
- Atualizar o Ventoy: `sudo sh Ventoy2Disk.sh -u /dev/disk/by-id/...` (preserva a
  partição de dados, segundo o Ventoy). Mesmo assim, mantenha backup.
