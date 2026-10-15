# extras/ — arquivos reais das pastas de apoio (fora do Git)

Coloque aqui os arquivos que irão para as pastas de apoio da mídia:

```
extras/DRIVERS/...        -> DRIVERS/ na mídia
extras/INSTALADORES/...   -> INSTALADORES/ na mídia
extras/FERRAMENTAS/...    -> FERRAMENTAS/ na mídia
extras/BIOS_FIRMWARE/...  -> BIOS_FIRMWARE/ na mídia
```

- O conteúdo é ignorado pelo Git (arquivos grandes e de terceiros).
- `scripts/prepare-staging.sh` leva estes arquivos para `build/staging/`
  (como link, por padrão; `--iso-mode copy` copia; `--iso-mode none` não leva).
- As regras de cada pasta estão em `media-layout/<PASTA>/LEIA-ME.txt`.
  Preencha o `INVENTARIO.csv` de cada pasta (em `extras/<PASTA>/INVENTARIO.csv`,
  que substitui o modelo vazio).
- **Não existe pasta CLIENTES.** O staging recusa `extras/CLIENTES`: dados de
  clientes ficam numa partição criptografada separada
  (`docs/instalacao-segura.md`, seção "Dados de clientes").
