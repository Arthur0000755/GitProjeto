# Arquitetura do AG Vexa Toolkit

Versão do documento: 0.1.0-rc1 · Base de referência: **Ventoy 1.1.18**

## 1. Visão geral

O AG Vexa Toolkit é uma **camada de organização e identidade** sobre o Ventoy.
O Ventoy é o carregador de boot (GRUB2 modificado) que inicia arquivos ISO
direto de uma partição de dados, sem extrair. O toolkit não altera o núcleo
do Ventoy: usa apenas os **plugins oficiais** lidos de `/ventoy/ventoy.json` e
o **menu estendido** `/ventoy/ventoy_grub.cfg` (tecla F6).

```
 ┌─────────────────────────── HD externo 320 GB (futuro) ─────────────────────────┐
 │ Partição 1 (exFAT, "dados")                          │ Partição 2 (VTOYEFI)   │
 │  ISO/<categoria>/*.iso   ← imagens verificadas        │  GRUB/EFI do Ventoy    │
 │  ventoy/ventoy.json      ← plugins: control, theme,   │  (instalada pelo       │
 │                            menu_alias, menu_class,    │   Ventoy2Disk; NUNCA   │
 │                            menu_tip                   │   editada pelo toolkit)│
 │  ventoy/ventoy_grub.cfg  ← menu F6 (informações)      │                        │
 │  ventoy/themes/agvexa/   ← tema principal             │                        │
 │  ventoy/themes/agvexa-lite/ ← tema leve (alternativo) │                        │
 │  AGVexa/                 ← docs, modelos, Optimizer   │                        │
 │  DRIVERS/ INSTALADORES/ FERRAMENTAS/ BIOS_FIRMWARE/   │                        │
 │                          ← apoio no Windows (extras/) │                        │
 │  SHA256SUMS-AGVEXA.txt   ← conferência pós-cópia      │                        │
 └───────────────────────────────────────────────────────┴────────────────────────┘
```

## 2. Separação de responsabilidades

| Camada | Onde fica no projeto | Vai para o HD? |
|---|---|---|
| 1. Sistema de inicialização | Ventoy oficial (baixado à parte, `vendor/` fora do Git) | instalado pelo Ventoy2Disk (Fase F) |
| 2. Tema e identidade visual | `ventoy/themes/`, `branding/`, `scripts/build-theme-assets.py` | sim (`ventoy/themes`) |
| 3. Catálogo de imagens | `catalog/ferramentas.yaml`, `catalog/isos-manifest*.json`, `isos/` (fora do Git) | ISOs verificadas + cópia do catálogo |
| 4. Configuração de boot | `catalog/categorias.json` → `ventoy/ventoy.json` (gerado) | sim (gerado no staging) |
| 5. Scripts de preparação/verificação | `scripts/` | não (ficam no servidor) |
| 6. Documentação técnica | `docs/` | sim (`AGVexa/docs`) |
| 7. Procedimentos operacionais | `docs/procedimentos-de-atendimento.md`, `templates/relatorios/` | sim |
| 8. Testes | `tests/`, `windows-optimizer/tests/` | só os do Optimizer |

Distinção de artefatos:

- **Fonte** (versionado): tudo exceto `isos/`, `build/`, `reports/`, `.cache/`, `vendor/`.
- **Destinado ao HD**: somente o conteúdo de `build/staging/`, montado por `scripts/prepare-staging.sh`.
- **ISOs**: em `isos/` (fora do Git), descritas em `catalog/isos-manifest.json` (fora do Git).
- **Gerados**: `ventoy/ventoy.json` (gerado e versionado, conferido por teste), imagens do tema, `build/`.
- **Relatórios**: `reports/` (fora do Git, podem conter dados de equipamentos).

## 3. Fluxo de trabalho

```
categorias.json ──(build-base)──► ventoy/ventoy.json (base, versionado)
isos/ + isos-manifest.json ──(verify-isos)──► VERIFICADA / NAO_VERIFICADA / DIVERGENTE ...
base + ISOs VERIFICADAS ──(prepare-staging)──► build/staging/ (layout exato do HD)
build/staging ──(validate-config --staging)──► conferência
build/staging ──(Fase F, manual, autorizada)──► HD externo
```

## 4. Recursos do Ventoy usados — e onde foram confirmados

O site ventoy.net não estava acessível a partir do ambiente de desenvolvimento
(bloqueio de rede). Por isso **cada recurso foi confirmado diretamente no
código-fonte oficial** (`github.com/ventoy/Ventoy`, commit `582704c`,
12/10/2026, `VENTOY_VERSION="1.1.18"`), que é a implementação real:

| Recurso | Uso no toolkit | Confirmação no código |
|---|---|---|
| Plugin `control` | menu em árvore, raiz `/ISO`, idioma `pt_BR`, filtro `._*`, política de Secure Boot, sem bypass do Win11 | `ventoy_plugin.c` (tabela de plugins, `ventoy_plugin_control_entry`), `Plugson/www/plugson_control.html`, `INSTALL/grub/menu/pt_BR.json` |
| `VTOY_DEFAULT_MENU_MODE=1` | abre direto em árvore (categorias) | `grub.cfg` e `ventoy_cmd.c` (`g_default_menu_mode`) |
| `VTOY_TREE_VIEW_MENU_STYLE=1` | remove prefixos "DIR"/tamanho | `plugson_control.html` |
| Pastas vazias ocultas | categorias sem ISO não aparecem | `ventoy_cmd.c`: `if (node->isocnt == 0 ...) return 0;` |
| `VTOY_SECURE_BOOT_POLICY=1` | seguir a política do firmware (mais seguro) | `SecureBoot.md`, `ventoy.c` |
| Plugin `theme` (`file` em lista, `default_file`, `gfxmode`, `display_mode`) | tema principal + tema leve; seleção via F5 | `ventoy_plugin_theme_entry`/`_check`; `default_file` é inteiro 1‑based |
| Caminho do tema | absoluto a partir da raiz da partição | `ventoy_plugin_theme_entry` (prefixa `isodisk`) |
| Plugin `menu_alias` (`dir`/`image`) | nomes "01 — Instalação de Sistemas" e nomes amigáveis das ISOs | comparação exata de caminho absoluto, sem barra final (`ventoy_cmd.c` remove a barra antes da consulta) |
| Plugin `menu_class` (`dir`/`parent`) | ícone por categoria, inclusive para as ISOs dentro dela | `ventoy_plugin_get_menu_class`, `ventoy_plugin_is_parent` |
| Plugin `menu_tip` (`left`,`top`,`color`,`tips[]` com `tip1`/`tip2`) | dica de 2 linhas por categoria/ISO | `ventoy_plugin_menutip_entry`, `theme_loader.c` |
| Limites | caminho/alias ≤ 255 bytes, dica ≤ 999, classe ≤ 63 | `ventoy_def.h` (`menu_alias`, `menu_tip`, `menu_class`) |
| Menu F6 `ventoy_grub.cfg` | informações, regras de segurança, identificação, reiniciar/desligar | `grub.cfg`: `ventoy_ext_menu` |
| Rótulos de tema `@VTOY_HOTKEY_TIP@` e `@@VARIAVEL` | linha de atalhos e versão real do Ventoy no rodapé | `gfxmenu/gui_label.c` |
| `desktop-image-scale-method`, `message-bg-color` | ajuste do fundo | `gfxmenu/theme_loader.c` |
| Fonte padrão | Ventoy carrega `unicode.pf2` ("Unknown Regular 16") em BIOS e UEFI | `grub.cfg` (loadfont) — por isso o tema não declara fontes |
| `.ventoyignore` | pasta `AGVexa/` nunca é varrida | `ventoy_cmd.c` (`ventoy_check_ignore_flag`) |
| `smbios`, `echo`, `read`, `reboot`, `halt` | comandos do menu F6 | presentes nas listas de módulos BIOS e UEFI (`GRUB2/MOD_SRC/grub-2.04/install.sh`). `cat` **não** existe no BIOS → não usado |
| Instalação em dispositivo loop | permite teste 100% virtual futuro | `INSTALL/tool/ventoy_lib.sh` trata `/dev/loop*` |

Recursos **não usados de propósito**: `auto_install`, `persistence`,
`injection`, `conf_replace`, `password`, `custom_boot`, `dud`,
`auto_memdisk`, `image_list`. São válidos, mas alteram o comportamento de
boot das ferramentas e exigiriam testes próprios. O validador avisa se
alguém os acrescentar.

## 5. Decisões e justificativas

| Decisão | Motivo |
|---|---|
| Ventoy como base | GPL‑3.0, sem mensalidade, funciona offline, suporta BIOS e UEFI, várias ISOs na mesma partição, plugins documentados. |
| Categorias por **pastas** + `menu_alias` | Menus aninhados reais sem modificar o Ventoy; pasta vazia some sozinha → nenhuma ferramenta inexistente aparece. |
| `ventoy.json` **gerado** | Evita erro de digitação em caminhos; o staging só inclui aliases de ISOs presentes e verificadas. |
| Somente ISOs VERIFICADAS no staging por padrão | Integridade acima da quantidade. `--allow-unverified` existe, mas marca o item com "[NÃO VERIFICADA]" no próprio menu. |
| Sem timeout / sem imagem padrão | O toolkit nunca inicia nada sozinho em computador de cliente (o validador recusa). |
| `VTOY_SECURE_BOOT_POLICY=1` | Com Secure Boot ativo e chave do Ventoy registrada, só arquivos EFI assinados iniciam. Ferramentas não assinadas exigem desativar o Secure Boot temporariamente, com autorização (procedimento em `compatibilidade.md`). Nunca automático. |
| `VTOY_WIN11_BYPASS_*=0` | Contornar requisitos do Windows 11 não é suportado pela Microsoft; decisão fica com o proprietário. |
| Tema desenhado para 1024×768 | É o `gfxmode` padrão do Ventoy e o mais compatível com máquinas antigas; percentuais adaptam outras resoluções. |
| Textos grandes renderizados no fundo | GRUB não escala fontes bitmap; título/subtítulo em PNG ficam nítidos sem depender de fontes `.pf2`. |
| Tema leve + modo texto como fallback | Degradação: tema completo → tema leve (sem imagem de fundo) → `F5 > Modo de Exibição > texto`. |
| Menu F6 com comandos restritos | Informação e segurança no próprio boot, sem risco: o validador recusa qualquer comando fora da lista. |
| Scripts em Bash + Python stdlib | Já presentes no Ubuntu Server; sem instalar pacotes. Pillow/PyYAML são opcionais. |
| Staging com links simbólicos | Economiza o SSD de 128 GB do servidor; a cópia para o HD segue os links. |

## 6. Limites conhecidos da arquitetura

- O item "07 — Informações do Toolkit" do exemplo conceitual **não pode** ser
  uma entrada do menu principal: o Ventoy só lista imagens e pastas. Ele foi
  implementado no **F6**, indicado no painel "Como usar" do fundo.
- Validação estática do JSON e do tema **não prova** que o boot funciona.
  Ver `plano-de-testes-boot.md` e `relatorio-de-validacao.md`.
- Ver também `riscos-e-limitacoes.md`.
