# Biblioteca local de ISOs (fora do Git)

Coloque aqui as imagens baixadas das **fontes oficiais**, uma subpasta por
ferramenta (ex.: `isos/systemrescue/`). Este diretório é ignorado pelo Git:
ISOs são grandes e algumas são proprietárias.

1. Baixe a ISO e, quando existir, o arquivo de checksums oficial
   (SHA256SUMS, CHECKSUMS.TXT, .sha256) para a mesma subpasta.
2. Registre o item em `catalog/isos-manifest.json`.
3. Rode `scripts/verify-isos.sh`.

Veja `docs/ferramentas.md` e `docs/manutencao.md`.
