# Ferramentas do AG Vexa Toolkit

Fonte de dados estruturada: `catalog/ferramentas.yaml` (validado por
`scripts/validate-config.sh`). Licenças em detalhe: `licencas.md`.
Uso de cada ferramenta: `manual-do-tecnico.md`.

## 1. Núcleo inicial (poucas ferramentas, confiáveis)

| Categoria do menu | Ferramenta | Licença | Origem | Status |
|---|---|---|---|---|
| 01 Instalação de Sistemas | Windows 11 | Proprietária | microsoft.com (técnico baixa) | incluída |
| 01 Instalação de Sistemas | Windows 10 | Proprietária | microsoft.com | opcional (fim do suporte regular) |
| 02 Diagnóstico de Hardware | MemTest86+ | GPL‑2.0 | memtest.org | incluída |
| 03 Manutenção de Discos | GParted Live | GPL | gparted.org | incluída |
| 04 Backup e Recuperação | Rescuezilla | GPL‑3.0 | rescuezilla.com | incluída |
| 05 Ambientes Linux Live | SystemRescue (smartctl, TestDisk, PhotoRec, ddrescue, rede) | GPL e outras livres | system-rescue.org | incluída |
| 05 Ambientes Linux Live | Ubuntu Desktop LTS | livres + política de marca | ubuntu.com | incluída |
| 06 Ferramentas Avançadas | Clonezilla Live | GPL | clonezilla.org | incluída |

Ferramentas **embutidas** (sem ISO própria): smartmontools, TestDisk, PhotoRec,
GNU ddrescue, ferramentas de rede — todas dentro do SystemRescue.

Por que não mais ferramentas? Cada ISO extra é mais uma coisa para verificar,
atualizar e testar. SystemRescue cobre a maior parte das necessidades de resgate.

## 2. Critérios de inclusão (aplicados a cada ferramenta)

| # | Critério | Como é verificado |
|---|---|---|
| 1 | Fonte oficial | `fonte_oficial` (https) no manifesto; download só do site/release oficial |
| 2 | Licença | `catalog/ferramentas.yaml` + `licencas.md` |
| 3 | Disponibilidade atual | reconferida a cada atualização (`manutencao.md`) |
| 4 | Compatibilidade com o modo de boot | `modos_boot`, `secure_boot`; testes físicos (`plano-de-testes-boot.md`) |
| 5 | Arquitetura | somente x86_64 nesta versão |
| 6 | Integridade do download | SHA‑256 oficial obrigatório para status VERIFICADA (`verify-isos.sh`) |
| 7 | Utilidade para assistência técnica | uso_principal no catálogo |
| 8 | Riscos operacionais | campo `riscos` + avisos no menu (dicas) e no manual |
| 9 | Necessidade de internet | campo `requer_internet` |
| 10 | Documentação básica de uso | seção correspondente no Manual do Técnico |

## 3. Como baixar e registrar uma ferramenta

1. Acesse **somente** o endereço oficial do catálogo.
2. Baixe a ISO **e** o arquivo de checksums oficial (`SHA256SUMS`, `CHECKSUMS.TXT`, `.sha256`), se houver.
3. Se o projeto publica assinatura GPG, confira-a (exemplo Ubuntu):
   ```bash
   gpg --keyid-format long --verify SHA256SUMS.gpg SHA256SUMS
   ```
   (a chave pública deve ser obtida da fonte oficial do projeto).
4. Salve em `isos/<ferramenta>/`.
5. Em `catalog/isos-manifest.json` (copiado do exemplo): ajuste `arquivo`, `versao` e
   preencha `sha256` **copiando da fonte oficial** — ou aponte `arquivo_checksums`.
6. Rode `scripts/verify-isos.sh` e confirme o status **VERIFICADA**.
7. Rode `scripts/prepare-staging.sh` e `scripts/validate-config.sh --staging build/staging`.

Windows: a Microsoft publica a lista de hashes SHA‑256 das ISOs na própria página
de download. Copie o valor correspondente ao idioma/edição baixados.

## 4. Itens em avaliação para versões futuras

- Ferramenta de inspeção de hardware dedicada (ex.: ambiente live com `hardinfo`/`lshw` gráfico).
- Teste de superfície de disco em modo somente leitura com relatório.
- Variante ARM64 (Ventoy suporta, mas não há demanda de clientes nesta fase).
