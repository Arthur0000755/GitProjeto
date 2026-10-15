# Logomarca oficial da AG Vexa

`agvexa-logo.png` é a logomarca oficial fornecida pelo proprietário
(PNG RGBA com fundo transparente, recortada nas bordas, 1352×662 px).
Versão para fundo escuro: letras claras com o "A" e a linha
"ASSISTÊNCIA TÉCNICA" em azul.

Onde é usada:

| Uso | Como |
|---|---|
| Fundo do tema do boot (`ventoy/themes/agvexa/background.png`) | composta por `scripts/build-theme-assets.py` (altura ~118 px em 1024×768) |
| Papéis de parede (`branding/backgrounds/`) | idem |
| Relatório HTML do Windows Optimizer | cópia reduzida em `windows-optimizer/assets/agvexa-logo.png`, embutida no HTML |

Para trocar a logo: substitua `agvexa-logo.png` (mantenha fundo transparente
e versão clara), rode `python3 scripts/build-theme-assets.py` e `tests/run-all.sh`.
Sem o arquivo, o gerador volta para a identificação tipográfica.

A logomarca é propriedade da AG Vexa e não está coberta pelas licenças das
fontes ou das ferramentas de terceiros.
