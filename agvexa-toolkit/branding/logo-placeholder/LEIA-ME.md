# Local reservado para a logomarca oficial da AG Vexa

A logomarca oficial **não foi fornecida**. Por isso o tema usa uma
**identificação tipográfica temporária** ("AG VEXA  ASSISTÊNCIA TÉCNICA" e
"AG VEXA TOOLKIT" em Inter Bold). Nenhuma logo nova foi criada.

## Como inserir a logo oficial

1. Salve a logo como `branding/logo-placeholder/logo-oficial.png`
   - PNG com transparência (RGBA), fundo transparente;
   - versão **clara** (para fundo escuro #0B1220);
   - altura mínima de 112 px (será reduzida para ~28 px no tema 1024×768).
2. Rode `python3 scripts/build-theme-assets.py`. O gerador detecta o arquivo e
   coloca a logo no lugar da linha "AG VEXA ASSISTÊNCIA TÉCNICA" do fundo.
3. Revise `docs/previews/preview-agvexa.png` e rode `tests/run-all.sh`.

O arquivo `logo-oficial.*` está no `.gitignore` por padrão: só versione
quando o proprietário autorizar (remova a linha correspondente do `.gitignore`).
