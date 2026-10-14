# Fontes e licenças da identidade visual

| Elemento | Origem | Licença | Onde é usado |
|---|---|---|---|
| Inter (Regular, SemiBold, Bold) | https://github.com/rsms/inter | SIL Open Font License 1.1 — `branding/fonts/LICENSE-Inter-OFL-1.1.txt` | textos renderizados nas imagens de fundo (PNG) |
| DejaVu Sans Mono | https://dejavu-fonts.github.io/ | Bitstream Vera + domínio público — `branding/fonts/LICENSE-DejaVu.txt` | apenas nas pré-visualizações (`docs/previews`) |
| Fonte do menu no boot | `unicode.pf2` distribuída com o Ventoy (GNU Unifont, "Unknown Regular 16") | licença do Ventoy/GNU Unifont | texto do menu (o toolkit não redistribui; já vem no Ventoy) |
| Fundos, molduras, ícones | criados para este projeto por `scripts/build-theme-assets.py` | propriedade da AG Vexa (licença a definir pelo proprietário) | tema e branding |

As fontes ficam versionadas em `branding/fonts/` para que as imagens possam
ser **regeneradas** de forma idêntica no servidor (a OFL permite redistribuir
junto com o software, mantendo o aviso de licença, desde que a fonte não seja
vendida isoladamente).

## Paleta

`branding/palette.json` — fundo #0B1220, secundário #111C30, destaque #38BDF8,
azul secundário #2563EB, texto #F8FAFC/#E2E8F0, texto secundário #94A3B8,
alerta #F59E0B, erro #EF4444. Contraste do item selecionado (branco sobre
#2563EB) ≈ 5,2:1 (atende WCAG AA para texto normal).

## Ícones

18 ícones originais (traço simples, 24 px no tema e 96 px em `branding/icons/`):
instalação, hardware, discos, backup, Linux, avançado, informações, segurança,
energia, reiniciar, pasta, voltar, ISO/WIM/VTOY (disco óptico), IMG/VHD (disco), EFI (chip).
