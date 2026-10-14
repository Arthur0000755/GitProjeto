# Manutenção do AG Vexa Toolkit

## 1. Rotina mensal (ou ao preparar a mídia)

1. `scripts/preflight.sh` — ambiente ok.
2. Verifique novas versões **no site oficial** de cada ferramenta (`catalog/ferramentas.yaml`).
3. Para cada atualização: baixe ISO + checksums oficiais → atualize o manifesto → `scripts/verify-isos.sh`.
4. `scripts/prepare-staging.sh` → `scripts/validate-config.sh --staging build/staging`.
5. Teste em VM (se disponível) e no equipamento de homologação.
6. Copie para o HD (`instalacao-segura.md`, etapas 7–8) e registre no `CHANGELOG.md`.

## 2. Atualizar o Ventoy

1. Leia as notas da nova release (mudanças em plugins podem afetar o tema/menu).
2. Confira o SHA‑256 publicado.
3. Se a versão mudou: atualize `VENTOY_REFERENCE_VERSION` em `scripts/lib/agvexa.py`
   **somente depois** de revisar no código-fonte novo os arquivos listados em
   `arquitetura.md` §4 (opções de controle, idiomas, tema).
4. Atualize o HD com `Ventoy2Disk.sh -u` (mantenha backup).

## 3. Alterar categorias ou textos do menu

1. Edite `catalog/categorias.json` (ids de pasta, nomes, dicas).
2. `scripts/prepare-staging.sh --rebuild-base` (regera `ventoy/ventoy.json`).
3. Se criou classe nova: acrescente o ícone em `scripts/build-theme-assets.py` (`ICON_CLASSES`) e rode o script.
4. `tests/run-all.sh`.

## 4. Alterar o visual

1. Paleta em `branding/palette.json`; desenho em `scripts/build-theme-assets.py`.
2. `python3 scripts/build-theme-assets.py` (requer Pillow).
3. Layout em `ventoy/themes/*/theme.txt`.
4. Revise `docs/previews/*.png` e teste em VM/hardware.

## 5. Nova versão do toolkit

1. Atualize `VERSION`, o rótulo de versão nos dois `theme.txt`, `ventoy/ventoy_grub.cfg`
   e `$script:AGVVersion` em `windows-optimizer/lib/AGVexa.Common.psm1`
   (os testes falham se algum ficar diferente).
2. `python3 scripts/build-theme-assets.py` (atualiza a prévia).
3. Registre no `CHANGELOG.md` e no `PROGRESSO.md`.

## 6. Limpeza

- `build/` pode ser apagado a qualquer momento (é regenerado).
- `reports/` contém relatórios locais: guarde pelo prazo combinado e apague.
- `.cache/sha256-cache.json` só acelera verificações; pode ser apagado.
