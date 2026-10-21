#!/usr/bin/env python3
"""Biblioteca central do AG Vexa Toolkit (somente biblioteca padrão do Python 3.8+).

Subcomandos (normalmente chamados pelos scripts .sh em scripts/):
  build-base     gera ventoy/ventoy.json a partir de catalog/categorias.json
  validate       valida configuração, temas, menu F6, catálogo e estrutura
  verify-isos    verifica ISOs contra o manifesto (existência, tipo, tamanho, SHA-256)
  stage          monta o diretório de staging (cópia futura para o HD) em build/

Regras de segurança deste módulo:
  * Nunca abre dispositivos de bloco (/dev/*) nem executa comandos externos.
  * Escreve apenas dentro do diretório do projeto (ventoy/ventoy.json, build/,
    reports/, .cache/).
  * Nunca apaga nada fora de um diretório de staging marcado com .agvexa-staging.
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import struct
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ------------------------------------------------------------------ constantes
# Fonte: código-fonte oficial do Ventoy 1.1.18
#   GRUB2/MOD_SRC/grub-2.04/grub-core/ventoy/ventoy_plugin.c (tabela de plugins)
#   Plugson/www/plugson_control.html (opções do plugin control)
VENTOY_REFERENCE_VERSION = "1.1.18"
PLUGINS = {"control", "theme", "auto_install", "persistence", "menu_alias", "menu_tip",
           "menu_class", "injection", "auto_memdisk", "image_list", "image_blacklist",
           "conf_replace", "dud", "password", "custom_boot"}
PLUGIN_SUFFIXES = ("", "_legacy", "_uefi", "_ia32", "_aa64", "_mips")
# Plugins que o AG Vexa Toolkit usa de propósito. Os demais são válidos no
# Ventoy, mas exigem revisão antes de serem adotados.
PLUGINS_USED = {"control", "theme", "menu_alias", "menu_tip", "menu_class"}

CONTROL_OPTIONS = {
    "VTOY_DEFAULT_MENU_MODE": {"0", "1"},
    "VTOY_TREE_VIEW_MENU_STYLE": {"0", "1"},
    "VTOY_FILT_DOT_UNDERSCORE_FILE": {"0", "1"},
    "VTOY_SORT_CASE_SENSITIVE": {"0", "1"},
    "VTOY_MAX_SEARCH_LEVEL": None,          # "max" ou inteiro >= 0
    "VTOY_DEFAULT_SEARCH_ROOT": None,       # caminho absoluto
    "VTOY_MENU_TIMEOUT": None,              # inteiro
    "VTOY_DEFAULT_IMAGE": None,             # caminho absoluto
    "VTOY_FILE_FLT_ISO": {"0", "1"},
    "VTOY_FILE_FLT_WIM": {"0", "1"},
    "VTOY_FILE_FLT_EFI": {"0", "1"},
    "VTOY_FILE_FLT_IMG": {"0", "1"},
    "VTOY_FILE_FLT_VHD": {"0", "1"},
    "VTOY_FILE_FLT_VTOY": {"0", "1"},
    "VTOY_MENU_LANGUAGE": None,
    "VTOY_SECONDARY_BOOT_MENU": {"0", "1"},
    "VTOY_SECONDARY_TIMEOUT": None,
    "VTOY_SHOW_PASSWORD_ASTERISK": {"0", "1"},
    "VTOY_VHD_NO_WARNING": {"0", "1"},
    "VTOY_WIN11_BYPASS_CHECK": {"0", "1"},
    "VTOY_WIN11_BYPASS_NRO": {"0", "1"},
    "VTOY_DEFAULT_KBD_LAYOUT": None,
    "VTOY_SECURE_BOOT_POLICY": {"0", "1"},
    "VTOY_WIN_UEFI_RES_LOCK": None,
}
MENU_LANGUAGES = {"ar_AR", "bn_BN", "cs_CZ", "de_DE", "el_GR", "en_US", "es_ES", "fa_IR", "fr_FR",
                  "hi_HI", "hr_HR", "hu_HU", "id_ID", "it_IT", "ja_JP", "ka_GE", "ko_KR", "lg_UG",
                  "pl_PL", "pt_BR", "pt_PT", "ru_RU", "sl_si", "sr_RS", "ta_IN", "tr_TR", "uk_UA",
                  "vi_VN", "zh_CN", "zh_TW"}
THEME_KEYS = {"file", "random", "default_file", "resolution_fit", "gfxmode", "display_mode",
              "serial_param", "ventoy_left", "ventoy_top", "ventoy_color", "fonts"}
DISPLAY_MODES = {"GUI", "CLI", "serial", "serial_console"}
GFXMODES = {"max", "1920x1080", "1680x1050", "1600x900", "1440x900", "1280x1024", "1280x960",
            "1024x768", "800x600"}
# Limites de buffer em ventoy_def.h (menu_alias/menu_tip/menu_class)
MAX_PATH_BYTES = 255
MAX_ALIAS_BYTES = 255
MAX_TIP_BYTES = 999
MAX_CLASS_BYTES = 63
# Classes de menu geradas pelo próprio Ventoy (ventoy_cmd.c)
VENTOY_BUILTIN_CLASSES = {"vtoydir", "vtoyret", "vtoyiso", "vtoywim", "vtoyefi", "vtoyimg",
                          "vtoyvhd", "vtoyvtoy"}

# Propriedades de tema confirmadas no GRUB 2.04 usado pelo Ventoy
# (theme_loader.c e componentes gfxmenu).
THEME_GLOBAL_PROPS = {"title-text", "title-font", "title-color", "message-font", "message-color",
                      "message-bg-color", "desktop-image", "desktop-image-scale-method",
                      "desktop-image-h-align", "desktop-image-v-align", "desktop-color",
                      "terminal-box", "terminal-border", "terminal-left", "terminal-top",
                      "terminal-width", "terminal-height", "terminal-font",
                      "menu-tip-left", "menu-tip-top", "menu-tip-color"}
THEME_COMPONENTS = {"boot_menu", "list", "label", "image", "vbox", "hbox", "canvas",
                    "progress_bar", "circular_progress"}
THEME_COMMON_PROPS = {"left", "top", "width", "height", "id"}
THEME_COMPONENT_PROPS = {
    "boot_menu": {"item_font", "selected_item_font", "item_color", "selected_item_color",
                  "icon_width", "icon_height", "item_height", "item_padding", "item_icon_space",
                  "item_spacing", "visible", "menu_pixmap_style", "item_pixmap_style",
                  "selected_item_pixmap_style", "scrollbar_frame", "scrollbar_thumb",
                  "scrollbar_thumb_overlay", "scrollbar_width", "scrollbar_slice",
                  "scrollbar_left_pad", "scrollbar_right_pad", "scrollbar_top_pad",
                  "scrollbar_bottom_pad", "scrollbar", "theme_dir"},
    "label": {"text", "font", "color", "align", "visible"},
    "image": {"file"},
    "progress_bar": {"fg_color", "bg_color", "border_color", "text_color", "bar_style",
                     "highlight_style", "highlight_overlay", "font", "text", "value", "start",
                     "end", "show_text"},
    "circular_progress": {"num_ticks", "start_angle", "ticks_disappear", "center_bitmap",
                          "tick_bitmap"},
    "vbox": set(), "hbox": set(), "canvas": set(),
}
THEME_COMPONENT_PROPS["list"] = THEME_COMPONENT_PROPS["boot_menu"]
NINE_SLICE = ("nw", "n", "ne", "w", "c", "e", "sw", "s", "se")
COLOR_NAMES = {"black", "blue", "green", "cyan", "red", "magenta", "brown", "light-gray",
               "dark-gray", "light-blue", "light-green", "light-cyan", "light-red",
               "light-magenta", "yellow", "white", "transparent", "gray", "grey", "orange",
               "purple", "silver", "navy", "maroon", "olive", "teal", "lime", "aqua", "fuchsia"}

# Comandos permitidos no menu F6 (ventoy_grub.cfg). Lista restrita: o menu
# do toolkit só exibe informações e oferece reiniciar/desligar.
F6_ALLOWED_COMMANDS = {"menuentry", "submenu", "echo", "read", "clear", "set", "unset", "if", "then",
                       "else", "elif", "fi", "smbios", "reboot", "halt", "sleep", "}", "{"}

CATEGORY_FILE = os.path.join(ROOT, "catalog", "categorias.json")
VENTOY_JSON = os.path.join(ROOT, "ventoy", "ventoy.json")
F6_CFG = os.path.join(ROOT, "ventoy", "ventoy_grub.cfg")
THEMES = ["agvexa", "agvexa-lite"]

ISO_STATUS_OK = "VERIFICADA"
ISO_STATUS_UNVERIFIED = "NAO_VERIFICADA"
ISO_STATUS_MISSING = "AUSENTE"
ISO_STATUS_MISMATCH = "DIVERGENTE"
ISO_STATUS_BADTYPE = "TIPO_INVALIDO"
ISO_STATUS_BADSIZE = "TAMANHO_DIVERGENTE"
ISO_STATUS_DISABLED = "DESABILITADA"
ISO_STATUS_UNCATALOGED = "NAO_CATALOGADA"
ISO_ERROR_STATUSES = {ISO_STATUS_MISMATCH, ISO_STATUS_BADTYPE, ISO_STATUS_BADSIZE}

EXIT_OK, EXIT_ERROR, EXIT_WARN, EXIT_USAGE = 0, 1, 2, 64


# ------------------------------------------------------------------ utilidades

class Report:
    """Acumula resultados de verificação (OK / AVISO / ERRO)."""

    def __init__(self, quiet=False):
        self.items = []
        self.quiet = quiet

    def _add(self, level, msg):
        self.items.append((level, msg))
        if not self.quiet:
            print("  [%s] %s" % (level, msg))

    def ok(self, msg):
        self._add("OK", msg)

    def warn(self, msg):
        self._add("AVISO", msg)

    def error(self, msg):
        self._add("ERRO", msg)

    @property
    def errors(self):
        return [m for lvl, m in self.items if lvl == "ERRO"]

    @property
    def warnings(self):
        return [m for lvl, m in self.items if lvl == "AVISO"]

    def exit_code(self):
        if self.errors:
            return EXIT_ERROR
        if self.warnings:
            return EXIT_WARN
        return EXIT_OK


def rel(path):
    """Caminho relativo ao projeto quando estiver dentro dele; absoluto caso contrário."""
    try:
        r = os.path.relpath(path, ROOT)
    except ValueError:
        return path
    return os.path.abspath(path) if r.startswith("..") else r


def load_json(path):
    with open(path, "rb") as fh:
        raw = fh.read()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError("%s começa com BOM UTF-8 (remova; o Ventoy pode não interpretar)" % rel(path))
    return json.loads(raw.decode("utf-8")), raw


def dump_json(data):
    # ensure_ascii=False: o parser JSON do Ventoy espera UTF-8 direto; não
    # há garantia documentada de suporte a escapes \\uXXXX.
    return json.dumps(data, ensure_ascii=False, indent=4) + "\n"


def ascii_menu(text):
    text = text.replace("—", "-").replace("–", "-").replace("•", "-")
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def nbytes(text):
    return len(text.encode("utf-8"))


def read_version():
    with open(os.path.join(ROOT, "VERSION"), encoding="utf-8") as fh:
        return fh.read().strip()


def is_inside(path, base):
    path = os.path.realpath(path)
    base = os.path.realpath(base)
    return path == base or path.startswith(base + os.sep)


# ------------------------------------------------------------------ ventoy.json

def load_categories():
    data, _ = load_json(CATEGORY_FILE)
    return data


def build_ventoy_config(categories, images=None, ascii_only=False):
    """Monta o dicionário do ventoy.json.

    images: lista de dicts {"path": "/ISO/<cat>/<arquivo>", "alias": str,
            "dica1": str, "dica2": str} de ISOs efetivamente presentes no staging.
    """
    fix = ascii_menu if ascii_only else (lambda s: s)
    root = categories["raiz_iso"].rstrip("/")
    cats = categories["categorias"]
    config = {
        "control": [
            {"VTOY_DEFAULT_MENU_MODE": "1"},
            {"VTOY_TREE_VIEW_MENU_STYLE": "1"},
            {"VTOY_DEFAULT_SEARCH_ROOT": root},
            {"VTOY_MENU_LANGUAGE": "pt_BR"},
            {"VTOY_FILT_DOT_UNDERSCORE_FILE": "1"},
            {"VTOY_SECURE_BOOT_POLICY": "1"},
            {"VTOY_WIN11_BYPASS_CHECK": "0"},
            {"VTOY_WIN11_BYPASS_NRO": "0"},
        ],
        "theme": {
            "file": ["/ventoy/themes/%s/theme.txt" % t for t in THEMES],
            "default_file": 1,
            "gfxmode": "1024x768",
            "display_mode": "GUI",
        },
        "menu_alias": [],
        "menu_class": [],
        "menu_tip": {"left": "5.5%", "top": "83%", "color": "#94A3B8", "tips": []},
    }
    for c in cats:
        d = "%s/%s" % (root, c["id"])
        config["menu_alias"].append({"dir": d, "alias": fix(c["alias"])})
        config["menu_class"].append({"dir": d, "class": c["classe"]})
        config["menu_class"].append({"parent": d, "class": c["classe"]})
        config["menu_tip"]["tips"].append({"dir": d, "tip1": fix(c["dica1"]), "tip2": fix(c["dica2"])})
    for img in images or []:
        config["menu_alias"].append({"image": img["path"], "alias": fix(img["alias"])})
        tip = {"image": img["path"]}
        if img.get("dica1"):
            tip["tip1"] = fix(img["dica1"])
        if img.get("dica2"):
            tip["tip2"] = fix(img["dica2"])
        if len(tip) > 1:
            config["menu_tip"]["tips"].append(tip)
    return config


def cmd_build_base(args):
    config = build_ventoy_config(load_categories())
    text = dump_json(config)
    if args.check:
        with open(VENTOY_JSON, encoding="utf-8") as fh:
            current = fh.read()
        if current != text:
            print("ERRO: ventoy/ventoy.json difere do gerado a partir de catalog/categorias.json.")
            print("      Rode: scripts/prepare-staging.sh --rebuild-base")
            return EXIT_ERROR
        print("OK: ventoy/ventoy.json corresponde a catalog/categorias.json")
        return EXIT_OK
    if args.dry_run:
        print("[dry-run] ventoy/ventoy.json seria reescrito (%d bytes)" % len(text.encode("utf-8")))
        return EXIT_OK
    with open(VENTOY_JSON, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print("gerado: ventoy/ventoy.json")
    return EXIT_OK


def media_to_local(media_path, media_root):
    """Converte caminho absoluto da mídia (/ventoy/...) em caminho local."""
    return os.path.join(media_root, media_path.lstrip("/"))


def validate_ventoy_json(path, media_root, report, theme_root=None, strict_images=False):
    """Valida um ventoy.json. media_root: diretório que representa a raiz da partição."""
    try:
        cfg, raw = load_json(path)
    except (ValueError, OSError) as exc:
        report.error("ventoy.json inválido: %s" % exc)
        return None
    report.ok("%s: JSON válido, UTF-8 sem BOM" % rel(path))
    if b"\\u" in raw:
        report.warn("ventoy.json contém escapes \\uXXXX; prefira UTF-8 direto")
    if not isinstance(cfg, dict):
        report.error("raiz do ventoy.json deve ser um objeto")
        return None

    for key in cfg:
        base = key
        for suf in PLUGIN_SUFFIXES[1:]:
            if key.endswith(suf):
                base = key[: -len(suf)]
        if base not in PLUGINS:
            report.error("plugin desconhecido no ventoy.json: '%s'" % key)
        elif base not in PLUGINS_USED:
            report.warn("plugin '%s' é válido no Ventoy, mas não faz parte do projeto; revise" % key)
        if key != base and key.startswith("control"):
            report.warn("'%s' substitui 'control' inteiro nesse modo de boot (documentação Ventoy)" % key)

    # ---- control
    control = cfg.get("control", [])
    seen = {}
    if not isinstance(control, list):
        report.error("'control' deve ser uma lista de objetos")
        control = []
    for entry in control:
        if not isinstance(entry, dict) or len(entry) != 1:
            report.error("cada item de 'control' deve ser um objeto com UMA chave: %r" % (entry,))
            continue
        (k, v), = entry.items()
        if not isinstance(v, str):
            report.error("valor de %s deve ser string (o Ventoy ignora outros tipos)" % k)
            continue
        if k not in CONTROL_OPTIONS:
            report.error("opção de control não documentada: %s" % k)
            continue
        allowed = CONTROL_OPTIONS[k]
        if allowed is not None and v not in allowed:
            report.error("%s=%r fora dos valores documentados %s" % (k, v, sorted(allowed)))
        if k in seen:
            report.warn("%s definido mais de uma vez" % k)
        seen[k] = v
    if "VTOY_MENU_LANGUAGE" in seen and seen["VTOY_MENU_LANGUAGE"] not in MENU_LANGUAGES:
        report.error("VTOY_MENU_LANGUAGE=%s não existe no Ventoy %s" % (seen["VTOY_MENU_LANGUAGE"], VENTOY_REFERENCE_VERSION))
    if "VTOY_MAX_SEARCH_LEVEL" in seen and not re.fullmatch(r"max|\d+", seen["VTOY_MAX_SEARCH_LEVEL"]):
        report.error("VTOY_MAX_SEARCH_LEVEL deve ser 'max' ou número")
    for k in ("VTOY_MENU_TIMEOUT", "VTOY_SECONDARY_TIMEOUT"):
        if k in seen and not re.fullmatch(r"\d+", seen[k]):
            report.error("%s deve ser número inteiro em string" % k)
    # Política de segurança do projeto
    if seen.get("VTOY_MENU_TIMEOUT", "0") != "0" or "VTOY_DEFAULT_IMAGE" in seen:
        report.error("POLÍTICA: o toolkit não pode iniciar imagens automaticamente "
                     "(remova VTOY_MENU_TIMEOUT/VTOY_DEFAULT_IMAGE)")
    if seen.get("VTOY_WIN11_BYPASS_CHECK") == "1" or seen.get("VTOY_WIN11_BYPASS_NRO") == "1":
        report.error("POLÍTICA: bypass de requisitos do Windows 11 só com decisão documentada do proprietário")
    if seen.get("VTOY_SECURE_BOOT_POLICY") != "1":
        report.warn("VTOY_SECURE_BOOT_POLICY não é '1' (seguir política do firmware); revise o risco")
    else:
        report.ok("Secure Boot: Ventoy configurado para seguir a política do firmware")
    search_root = seen.get("VTOY_DEFAULT_SEARCH_ROOT")
    if search_root is not None:
        if not search_root.startswith("/") or search_root.rstrip("/") == "":
            report.error("VTOY_DEFAULT_SEARCH_ROOT deve ser um subdiretório absoluto (ex.: /ISO)")
        elif media_root and not os.path.isdir(media_to_local(search_root, media_root)):
            report.warn("diretório de busca %s ainda não existe em %s" % (search_root, rel(media_root)))
    if seen:
        report.ok("control: %d opções documentadas" % len(seen))

    # ---- theme
    theme = cfg.get("theme")
    theme_files = []
    if theme is not None:
        if not isinstance(theme, dict):
            report.error("'theme' deve ser objeto")
        else:
            for k in theme:
                if k not in THEME_KEYS:
                    report.error("chave de theme não documentada: %s" % k)
            files = theme.get("file")
            if isinstance(files, str):
                files = [files]
            if not files:
                report.error("theme.file ausente")
                files = []
            for f in files:
                if not isinstance(f, str):
                    report.error("theme.file deve conter strings")
                    continue
                if nbytes(f) > MAX_PATH_BYTES:
                    report.error("caminho de tema longo demais: %s" % f)
                local = media_to_local(f if f.startswith("/") else "/ventoy/" + f, theme_root or media_root)
                if os.path.isfile(local):
                    report.ok("tema encontrado: %s" % f)
                    theme_files.append(local)
                else:
                    report.error("arquivo de tema não encontrado: %s (procurado em %s)" % (f, rel(local)))
            df = theme.get("default_file")
            if df is not None and (not isinstance(df, int) or df < 0 or df > len(files)):
                report.error("theme.default_file deve ser inteiro entre 0 e %d" % len(files))
            rf = theme.get("resolution_fit")
            if rf is not None and rf not in (0, 1):
                report.error("theme.resolution_fit deve ser 0 ou 1")
            if theme.get("display_mode", "GUI") not in DISPLAY_MODES:
                report.error("theme.display_mode inválido: %s" % theme.get("display_mode"))
            gm = theme.get("gfxmode")
            if gm is not None and gm not in GFXMODES:
                report.warn("gfxmode %s não está na lista documentada pelo Plugson" % gm)
            for fnt in theme.get("fonts", []) or []:
                if not os.path.isfile(media_to_local(fnt, theme_root or media_root)):
                    report.error("fonte declarada não existe: %s" % fnt)

    # ---- menu_alias / menu_class / menu_tip
    classes = set()
    for entry in cfg.get("menu_alias", []) or []:
        key = "image" if "image" in entry else "dir"
        p = entry.get(key)
        alias = entry.get("alias")
        if not p or not alias:
            report.error("menu_alias precisa de image|dir e alias: %r" % (entry,))
            continue
        if not p.startswith("/"):
            report.error("menu_alias: caminho deve ser absoluto (começar com /): %s" % p)
        if p.endswith("/"):
            report.error("menu_alias: diretório sem barra final (comparação exata no Ventoy): %s" % p)
        if nbytes(p) > MAX_PATH_BYTES or nbytes(alias) > MAX_ALIAS_BYTES:
            report.error("menu_alias excede limite de 255 bytes: %s" % p)
        if "\\" in p:
            report.error("use '/' nos caminhos: %s" % p)
        if strict_images and key == "image" and not os.path.isfile(media_to_local(p, media_root)):
            report.error("menu_alias aponta para imagem inexistente: %s" % p)
    for entry in cfg.get("menu_class", []) or []:
        keys = [k for k in ("key", "parent", "dir") if k in entry]
        cls = entry.get("class")
        if len(keys) != 1 or not cls:
            report.error("menu_class precisa de exatamente um entre key/parent/dir e de class: %r" % (entry,))
            continue
        if keys[0] in ("parent", "dir") and not entry[keys[0]].startswith("/"):
            report.error("menu_class.%s deve ser absoluto: %s" % (keys[0], entry[keys[0]]))
        if nbytes(cls) > MAX_CLASS_BYTES:
            report.error("classe longa demais: %s" % cls)
        classes.add(cls)
    tips = cfg.get("menu_tip")
    if tips is not None:
        if not isinstance(tips, dict) or not isinstance(tips.get("tips"), list):
            report.error("menu_tip deve ser objeto com lista 'tips'")
        else:
            for t in tips["tips"]:
                p = t.get("image") or t.get("dir")
                if not p or not p.startswith("/"):
                    report.error("menu_tip: image/dir absoluto obrigatório: %r" % (t,))
                for k in ("tip", "tip1", "tip2"):
                    if k in t and nbytes(t[k]) > MAX_TIP_BYTES:
                        report.error("menu_tip.%s longo demais em %s" % (k, p))
                    if k in t and len(t[k]) > 90:
                        report.warn("dica com mais de 90 caracteres pode ser cortada na tela: %s" % p)
            for k in ("left", "top"):
                if k in tips and not re.fullmatch(r"\d+(\.\d+)?%([+-]\d+)?|\d+", str(tips[k])):
                    report.error("menu_tip.%s em formato inesperado: %s" % (k, tips[k]))

    # ícones para todas as classes, em todos os temas
    for tf in theme_files:
        icon_dir = os.path.join(os.path.dirname(tf), "icons")
        missing = sorted(c for c in classes | VENTOY_BUILTIN_CLASSES
                         if not os.path.isfile(os.path.join(icon_dir, c + ".png")))
        if missing:
            report.warn("tema %s sem ícone para: %s" % (rel(os.path.dirname(tf)), ", ".join(missing)))
        else:
            report.ok("ícones completos em %s" % rel(icon_dir))
    return cfg


# ------------------------------------------------------------------ PNG / tema

def png_info(path):
    """Lê o cabeçalho IHDR. Retorna (largura, altura, profundidade, tipo_cor, entrelaçado)."""
    with open(path, "rb") as fh:
        head = fh.read(33)
    if head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        raise ValueError("não é PNG válido")
    w, h, depth, ctype, _comp, _filt, interlace = struct.unpack(">IIBBBBB", head[16:29])
    return w, h, depth, ctype, interlace


def check_png(path, report):
    try:
        w, h, depth, ctype, interlace = png_info(path)
    except (OSError, ValueError) as exc:
        report.error("%s: %s" % (rel(path), exc))
        return
    # O leitor PNG do GRUB 2.04 aceita 8 bits RGB/RGBA (e cinza) sem entrelaçamento.
    if depth != 8 or ctype not in (0, 2, 4, 6) or interlace != 0:
        report.error("%s: PNG %d bits tipo %d entrelaçado=%d (use 8 bits RGB/RGBA sem entrelaçamento)"
                     % (rel(path), depth, ctype, interlace))


def parse_theme(text):
    """Analisa um theme.txt do GRUB. Retorna (globais, componentes, erros)."""
    globals_, comps, errors = {}, [], []
    tokens = re.findall(r'"(?:[^"\\]|\\.)*"|\{|\}|=|:|[^\s{}=:"]+|\n', re.sub(r"(?m)^[ \t]*#[^\n]*", "", text))
    stack = []
    i = 0

    while i < len(tokens):
        tok = tokens[i]
        if tok == "\n":
            i += 1
            continue
        if tok == "+":
            if i + 2 >= len(tokens):
                errors.append("componente incompleto no fim do arquivo")
                break
            name = tokens[i + 1]
            j = i + 2
            while j < len(tokens) and tokens[j] == "\n":
                j += 1
            if j >= len(tokens) or tokens[j] != "{":
                errors.append("esperado '{' após '+ %s'" % name)
                i = j
                continue
            comp = {"type": name, "props": {}, "children": []}
            if stack:
                stack[-1]["children"].append(comp)
            else:
                comps.append(comp)
            stack.append(comp)
            i = j + 1
            continue
        if tok == "}":
            if not stack:
                errors.append("'}' sem abertura correspondente")
            else:
                stack.pop()
            i += 1
            continue
        # propriedade: nome (=|:) valor
        if i + 2 < len(tokens) and tokens[i + 1] in ("=", ":"):
            name, sep, value = tok, tokens[i + 1], tokens[i + 2]
            if value.startswith('"'):
                value = value[1:-1]
            else:
                # valores sem aspas podem ter várias partes (ex.: 95%-25)
                k = i + 3
                while k < len(tokens) and tokens[k] not in ("\n", "}", "+") and not (
                        k + 1 < len(tokens) and tokens[k + 1] in ("=", ":")):
                    value += tokens[k]
                    k += 1
                i = k - 3
            if stack:
                stack[-1]["props"][name] = value
            else:
                if sep != ":":
                    errors.append("propriedade global '%s' deve usar ':'" % name)
                globals_[name] = value
            i += 3
            continue
        errors.append("token inesperado: %r" % tok)
        i += 1
    if stack:
        errors.append("chaves '{' não fechadas: %d" % len(stack))
    return globals_, comps, errors


def valid_color(value):
    return bool(re.fullmatch(r"#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?|#[0-9A-Fa-f]{3}", value)) or value in COLOR_NAMES


def validate_theme(theme_txt, report, expected_version=None):
    theme_dir = os.path.dirname(theme_txt)
    with open(theme_txt, encoding="utf-8") as fh:
        text = fh.read()
    globals_, comps, errors = parse_theme(text)
    for e in errors:
        report.error("%s: %s" % (rel(theme_txt), e))
    for k, v in globals_.items():
        if k not in THEME_GLOBAL_PROPS:
            report.error("%s: propriedade global desconhecida '%s'" % (rel(theme_txt), k))
        if k.endswith("color") and not valid_color(v):
            report.error("%s: cor inválida %s=%s" % (rel(theme_txt), k, v))
    if "desktop-image" in globals_:
        img = os.path.join(theme_dir, globals_["desktop-image"])
        if os.path.isfile(img):
            check_png(img, report)
        else:
            report.error("%s: desktop-image não encontrado: %s" % (rel(theme_txt), globals_["desktop-image"]))
    else:
        if "desktop-color" not in globals_:
            report.warn("%s: sem desktop-image nem desktop-color" % rel(theme_txt))
    styles = []
    if "terminal-box" in globals_:
        styles.append(globals_["terminal-box"])
    has_menu = False
    labels = []

    def walk(comp):
        nonlocal has_menu
        t = comp["type"]
        if t not in THEME_COMPONENTS:
            report.error("%s: componente desconhecido '+ %s'" % (rel(theme_txt), t))
            return
        if t == "boot_menu":
            has_menu = True
        allowed = THEME_COMPONENT_PROPS.get(t, set()) | THEME_COMMON_PROPS
        for k, v in comp["props"].items():
            if k not in allowed:
                report.error("%s: propriedade '%s' não suportada em %s" % (rel(theme_txt), k, t))
            if (k.endswith("color") or k == "color") and not valid_color(v):
                report.error("%s: cor inválida %s=%s em %s" % (rel(theme_txt), k, v, t))
            if k.endswith("pixmap_style") or k in ("scrollbar_thumb", "scrollbar_frame"):
                styles.append(v)
            if k in ("left", "top", "width", "height") and not re.fullmatch(r"[0-9.%+\-]+", v):
                report.error("%s: posição inválida %s=%s" % (rel(theme_txt), k, v))
        if t == "label":
            labels.append(comp["props"].get("text", ""))
        if t == "image" and "file" in comp["props"]:
            f = os.path.join(theme_dir, comp["props"]["file"])
            if not os.path.isfile(f):
                report.error("%s: imagem não encontrada: %s" % (rel(theme_txt), comp["props"]["file"]))
        for ch in comp["children"]:
            walk(ch)

    for c in comps:
        walk(c)
    if not has_menu:
        report.error("%s: tema sem '+ boot_menu'" % rel(theme_txt))
    for style in styles:
        if "*" in style:
            found = [os.path.join(theme_dir, style.replace("*", p)) for p in NINE_SLICE]
            present = [f for f in found if os.path.isfile(f)]
            if not present:
                report.error("%s: nenhuma imagem para o estilo %s" % (rel(theme_txt), style))
            for f in present:
                check_png(f, report)
        else:
            f = os.path.join(theme_dir, style)
            if not os.path.isfile(f):
                report.error("%s: imagem não encontrada: %s" % (rel(theme_txt), style))
    icon_dir = os.path.join(theme_dir, "icons")
    if os.path.isdir(icon_dir):
        for f in sorted(os.listdir(icon_dir)):
            if f.endswith(".png"):
                check_png(os.path.join(icon_dir, f), report)
    if expected_version:
        if not any(expected_version in lbl for lbl in labels):
            report.error("%s: rodapé não exibe a versão %s (atualize o label)" % (rel(theme_txt), expected_version))
    if not errors:
        report.ok("%s: sintaxe e referências válidas (%d componentes)" % (rel(theme_txt), len(comps)))


def validate_f6(path, report, expected_version=None):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    depth = 0
    entries = 0
    for n, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        # remove strings para analisar a estrutura
        bare = re.sub(r"'[^']*'|\"[^\"]*\"", "''", s)
        depth += bare.count("{") - bare.count("}")
        if depth < 0:
            report.error("%s:%d: '}' sem abertura" % (rel(path), n))
            depth = 0
        word = bare.split()[0]
        if word in ("menuentry", "submenu"):
            entries += 1
        if word not in F6_ALLOWED_COMMANDS:
            report.error("%s:%d: comando '%s' fora da lista permitida para o menu F6" % (rel(path), n, word))
    if depth != 0:
        report.error("%s: chaves desbalanceadas" % rel(path))
    if expected_version and expected_version not in text:
        report.error("%s: versão %s não aparece no menu de informações" % (rel(path), expected_version))
    if entries:
        report.ok("%s: %d entradas, apenas comandos informativos/energia" % (rel(path), entries))


# ------------------------------------------------------------------ manifesto / ISOs

def load_manifest(path, report=None):
    data, _ = load_json(path)
    if data.get("schema") != "agvexa-isos-manifest/1":
        raise ValueError("schema do manifesto desconhecido: %r" % data.get("schema"))
    return data


def validate_manifest(path, report, categories):
    try:
        data = load_manifest(path)
    except (ValueError, OSError) as exc:
        report.error("manifesto %s: %s" % (rel(path), exc))
        return None
    cat_ids = {c["id"] for c in categories["categorias"]}
    ids = set()
    required = ("id", "nome", "categoria", "arquivo", "alias_menu", "fonte_oficial", "licenca",
                "redistribuicao", "habilitado")
    for item in data.get("itens", []):
        for k in required:
            if k not in item:
                report.error("manifesto: item %s sem campo '%s'" % (item.get("id", "?"), k))
        iid = item.get("id")
        if iid in ids:
            report.error("manifesto: id duplicado %s" % iid)
        ids.add(iid)
        if item.get("categoria") not in cat_ids:
            report.error("manifesto: %s com categoria inexistente %s" % (iid, item.get("categoria")))
        if not str(item.get("fonte_oficial", "")).startswith("https://"):
            report.error("manifesto: %s deve declarar fonte oficial https://" % iid)
        sha = item.get("sha256")
        if sha is not None and not re.fullmatch(r"[0-9a-fA-F]{64}", str(sha)):
            report.error("manifesto: %s com sha256 em formato inválido" % iid)
        arq = str(item.get("arquivo", ""))
        if arq.startswith("/") or ".." in arq.split("/") or "\\" in arq:
            report.error("manifesto: %s com caminho de arquivo inseguro: %s" % (iid, arq))
        if os.path.splitext(arq)[1].lower() not in (".iso", ".img"):
            report.error("manifesto: %s deve apontar para .iso ou .img" % iid)
        if nbytes(item.get("alias_menu", "")) > MAX_ALIAS_BYTES:
            report.error("manifesto: alias de %s longo demais" % iid)
        if str(item.get("redistribuicao", "")).lower().startswith("proibida") and item.get("incluir_no_git"):
            report.error("manifesto: %s é proprietário e não pode ir para o Git" % iid)
    report.ok("manifesto %s: %d itens" % (rel(path), len(data.get("itens", []))))
    return data


def detect_type(path):
    """Identifica ISO 9660 (assinatura CD001) ou imagem de disco (MBR/GPT). Somente leitura."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(0x9006)
    except OSError:
        return None
    for off in (0x8001, 0x8801, 0x9001):
        if head[off:off + 5] == b"CD001":
            return "iso9660"
    if len(head) >= 520 and head[512:520] == b"EFI PART":
        return "disco-gpt"
    if len(head) >= 512 and head[510:512] == b"\x55\xaa":
        return "disco-mbr"
    return None


def sha256_file(path, cache, progress=False):
    st = os.stat(path)
    key = os.path.realpath(path)
    hit = cache.get(key)
    if hit and hit.get("size") == st.st_size and hit.get("mtime_ns") == st.st_mtime_ns:
        return hit["sha256"], True
    h = hashlib.sha256()
    done = 0
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(4 * 1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
            done += len(chunk)
            if progress and st.st_size > 256 * 1024 * 1024 and done % (256 * 1024 * 1024) < len(chunk):
                sys.stdout.write("\r    calculando SHA-256: %3d%%" % (done * 100 // st.st_size))
                sys.stdout.flush()
    if progress and st.st_size > 256 * 1024 * 1024:
        sys.stdout.write("\r" + " " * 40 + "\r")
    digest = h.hexdigest()
    cache[key] = {"size": st.st_size, "mtime_ns": st.st_mtime_ns, "sha256": digest}
    return digest, False


def parse_checksums_file(path):
    """Lê arquivo de checksums oficial (formato GNU 'hash  nome' ou BSD 'SHA256 (nome) = hash')."""
    sums = {}
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            m = re.fullmatch(r"([0-9a-fA-F]{64})\s+\*?(.+)", line)
            if m:
                sums[os.path.basename(m.group(2).strip())] = m.group(1).lower()
                continue
            m = re.fullmatch(r"SHA256\s*\((.+)\)\s*=\s*([0-9a-fA-F]{64})", line)
            if m:
                sums[os.path.basename(m.group(1).strip())] = m.group(2).lower()
    return sums


def verify_isos(manifest_path, library, use_cache=True, progress=True, quiet=False):
    manifest = load_manifest(manifest_path)
    cache_path = os.path.join(ROOT, ".cache", "sha256-cache.json")
    cache = {}
    if use_cache and os.path.isfile(cache_path):
        try:
            cache, _ = load_json(cache_path)
        except ValueError:
            cache = {}
    results = []
    known = set()
    for item in manifest.get("itens", []):
        r = {"id": item["id"], "nome": item["nome"], "arquivo": item["arquivo"],
             "categoria": item["categoria"], "fonte_oficial": item.get("fonte_oficial"),
             "sha256_esperado": (item.get("sha256") or "").lower() or None,
             "sha256_calculado": None, "tamanho": None, "tipo": None, "status": None, "detalhe": ""}
        path = os.path.join(library, item["arquivo"])
        known.add(os.path.realpath(path))
        if not item.get("habilitado", True):
            r["status"] = ISO_STATUS_DISABLED
            r["detalhe"] = "item desabilitado no manifesto"
            results.append(r)
            continue
        if not os.path.isfile(path):
            r["status"] = ISO_STATUS_MISSING
            r["detalhe"] = "arquivo não encontrado na biblioteca"
            results.append(r)
            continue
        r["tamanho"] = os.path.getsize(path)
        ext = os.path.splitext(path)[1].lower()
        r["tipo"] = detect_type(path)
        if ext == ".iso" and r["tipo"] != "iso9660" and r["tipo"] not in ("disco-mbr", "disco-gpt"):
            r["status"] = ISO_STATUS_BADTYPE
            r["detalhe"] = "extensão .iso sem assinatura ISO 9660 nem tabela de partição"
            results.append(r)
            continue
        if ext == ".img" and r["tipo"] not in ("disco-mbr", "disco-gpt", "iso9660"):
            r["status"] = ISO_STATUS_BADTYPE
            r["detalhe"] = "imagem .img sem MBR/GPT reconhecível"
            results.append(r)
            continue
        if item.get("tamanho_bytes") and int(item["tamanho_bytes"]) != r["tamanho"]:
            r["status"] = ISO_STATUS_BADSIZE
            r["detalhe"] = "tamanho %d difere do declarado %d" % (r["tamanho"], int(item["tamanho_bytes"]))
            results.append(r)
            continue
        expected = r["sha256_esperado"]
        source = "manifesto"
        if not expected and item.get("arquivo_checksums"):
            sums_path = os.path.join(library, item["arquivo_checksums"])
            if os.path.isfile(sums_path):
                expected = parse_checksums_file(sums_path).get(os.path.basename(path))
                source = "arquivo oficial %s" % item["arquivo_checksums"]
                r["sha256_esperado"] = expected
        if not quiet:
            print("  - %s: calculando SHA-256 ..." % item["arquivo"])
        digest, cached = sha256_file(path, cache, progress=progress and not quiet)
        r["sha256_calculado"] = digest
        if not expected:
            r["status"] = ISO_STATUS_UNVERIFIED
            r["detalhe"] = "sem checksum oficial registrado; integridade NÃO comprovada"
        elif digest == expected:
            r["status"] = ISO_STATUS_OK
            r["detalhe"] = "SHA-256 confere com %s%s" % (source, " (cache)" if cached else "")
        else:
            r["status"] = ISO_STATUS_MISMATCH
            r["detalhe"] = "SHA-256 DIFERENTE do oficial (%s): não use este arquivo" % source
        results.append(r)
    # arquivos presentes na biblioteca que não estão no manifesto
    if os.path.isdir(library):
        for dirpath, _dirs, files in os.walk(library):
            for f in files:
                p = os.path.join(dirpath, f)
                if os.path.splitext(f)[1].lower() in (".iso", ".img") and os.path.realpath(p) not in known:
                    results.append({"id": None, "nome": None, "arquivo": os.path.relpath(p, library),
                                    "categoria": None, "status": ISO_STATUS_UNCATALOGED,
                                    "detalhe": "arquivo fora do manifesto (não será usado)"})
    if use_cache:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as fh:
            json.dump(cache, fh, indent=1)
    return results


def cmd_verify_isos(args):
    library = os.path.abspath(args.library)
    print("AG Vexa Toolkit - verificação de ISOs")
    print("  manifesto : %s" % rel(args.manifest))
    print("  biblioteca: %s" % library)
    try:
        results = verify_isos(args.manifest, library, use_cache=not args.no_cache, quiet=args.quiet)
    except (ValueError, OSError) as exc:
        print("ERRO: %s" % exc)
        return EXIT_ERROR
    print("")
    print("  %-22s %-20s %s" % ("STATUS", "ID", "ARQUIVO / DETALHE"))
    for r in results:
        print("  %-22s %-20s %s" % (r["status"], r["id"] or "-", r["arquivo"]))
        print("  %-22s %-20s   %s" % ("", "", r["detalhe"]))
    counts = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print("")
    print("  Resumo: " + ", ".join("%s=%d" % kv for kv in sorted(counts.items())))
    if args.report_dir:
        os.makedirs(args.report_dir, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        out = os.path.join(args.report_dir, "verificacao-isos-%s.json" % stamp)
        with open(out, "w", encoding="utf-8") as fh:
            json.dump({"gerado_em": stamp, "manifesto": rel(args.manifest), "biblioteca": library,
                       "resultados": results}, fh, ensure_ascii=False, indent=2)
        latest = os.path.join(args.report_dir, "verificacao-isos-ultima.json")
        shutil.copyfile(out, latest)
        print("  Relatório: %s" % rel(out))
    if any(r["status"] in ISO_ERROR_STATUSES for r in results):
        return EXIT_ERROR
    if any(r["status"] in (ISO_STATUS_UNVERIFIED, ISO_STATUS_MISSING, ISO_STATUS_UNCATALOGED) for r in results):
        return EXIT_WARN
    return EXIT_OK


# ------------------------------------------------------------------ validate

REQUIRED_PATHS = [
    "README.md", "CHANGELOG.md", "PROGRESSO.md", "VERSION", ".gitignore",
    "docs/arquitetura.md", "docs/instalacao-segura.md", "docs/manual-do-tecnico.md",
    "docs/ferramentas.md", "docs/compatibilidade.md", "docs/riscos-e-limitacoes.md",
    "docs/manutencao.md", "docs/relatorio-de-validacao.md", "docs/relatorio-de-seguranca.md",
    "docs/procedimentos-de-atendimento.md", "docs/licencas.md", "docs/plano-de-testes-boot.md",
    "docs/windows-optimizer.md", "docs/hd-arquivo-1tb.md", "docs/uso-no-windows.md",
    "branding/palette.json", "branding/fontes-e-licencas.md", "branding/logo/LEIA-ME.md", "branding/logo/agvexa-logo.png",
    "ventoy/ventoy.json", "ventoy/ventoy_grub.cfg",
    "ventoy/themes/agvexa/theme.txt", "ventoy/themes/agvexa-lite/theme.txt",
    "catalog/categorias.json", "catalog/ferramentas.yaml", "catalog/isos-manifest.example.json",
    "media-layout/LEIA-ME.txt", "media-layout/AGVexa/.ventoyignore", "extras/LEIA-ME.md",
    "media-layout/DRIVERS/LEIA-ME.txt", "media-layout/INSTALADORES/LEIA-ME.txt",
    "media-layout/FERRAMENTAS/LEIA-ME.txt", "media-layout/BIOS_FIRMWARE/LEIA-ME.txt",
    "scripts/preflight.sh", "scripts/validate-config.sh", "scripts/verify-isos.sh",
    "scripts/prepare-staging.sh", "scripts/test-boot.sh",
    "templates/relatorios",
    "windows-optimizer/AGVexa-Optimizer.ps1",
]


def validate_catalog_yaml(path, report, manifest):
    try:
        import yaml  # noqa: PLC0415 - dependência opcional
    except ImportError:
        report.warn("PyYAML ausente: catalog/ferramentas.yaml não foi analisado (instale python3-yaml)")
        return
    try:
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except Exception as exc:  # noqa: BLE001
        report.error("ferramentas.yaml inválido: %s" % exc)
        return
    tools = data.get("ferramentas", [])
    ids = {t.get("id") for t in tools}
    need = ("id", "nome", "projeto_oficial", "licenca", "redistribuicao", "status",
            "uso_principal", "riscos", "requer_internet")
    for t in tools:
        for k in need:
            if k not in t:
                report.error("ferramentas.yaml: %s sem campo '%s'" % (t.get("id", "?"), k))
        if t.get("status") not in ("incluida", "embutida", "opcional", "em_avaliacao", "rejeitada"):
            report.error("ferramentas.yaml: status inválido em %s" % t.get("id"))
    if manifest:
        for item in manifest.get("itens", []):
            if item["id"] not in ids:
                report.error("ferramentas.yaml não documenta o item do manifesto '%s'" % item["id"])
    report.ok("ferramentas.yaml: %d ferramentas documentadas" % len(tools))


def cmd_validate(args):
    report = Report(quiet=args.quiet)
    version = read_version()
    print("AG Vexa Toolkit %s - validação de configuração" % version)

    print("\n[1] Estrutura do projeto")
    for p in REQUIRED_PATHS:
        if not os.path.exists(os.path.join(ROOT, p)):
            report.error("ausente: %s" % p)
    report.ok("estrutura conferida (%d itens obrigatórios)" % len(REQUIRED_PATHS))
    if not re.fullmatch(r"\d+\.\d+\.\d+(-[0-9A-Za-z.]+)?", version):
        report.error("VERSION fora do padrão semântico: %s" % version)

    print("\n[2] Categorias e ventoy.json base")
    categories = load_categories()
    expected = dump_json(build_ventoy_config(categories))
    with open(VENTOY_JSON, encoding="utf-8") as fh:
        if fh.read() != expected:
            report.error("ventoy/ventoy.json desatualizado em relação a catalog/categorias.json "
                         "(rode scripts/prepare-staging.sh --rebuild-base)")
        else:
            report.ok("ventoy/ventoy.json gerado a partir de catalog/categorias.json")
    # No repositório, '/ventoy/...' corresponde a ROOT/ventoy/...
    validate_ventoy_json(VENTOY_JSON, None, report, theme_root=ROOT)

    print("\n[3] Temas")
    for t in THEMES:
        validate_theme(os.path.join(ROOT, "ventoy", "themes", t, "theme.txt"), report, version)

    print("\n[4] Menu F6 (ventoy_grub.cfg)")
    validate_f6(F6_CFG, report, version)

    print("\n[5] Catálogo e manifesto")
    manifest = validate_manifest(os.path.join(ROOT, "catalog", "isos-manifest.example.json"), report, categories)
    real = os.path.join(ROOT, "catalog", "isos-manifest.json")
    if os.path.isfile(real):
        validate_manifest(real, report, categories)
    else:
        report.warn("catalog/isos-manifest.json ainda não criado (copie do exemplo quando baixar as ISOs)")
    validate_catalog_yaml(os.path.join(ROOT, "catalog", "ferramentas.yaml"), report, manifest)

    if args.staging:
        print("\n[6] Staging %s" % args.staging)
        validate_staging(os.path.abspath(args.staging), report)

    print("\nResultado: %d erro(s), %d aviso(s)" % (len(report.errors), len(report.warnings)))
    return report.exit_code()


def validate_staging(staging, report):
    if not os.path.isfile(os.path.join(staging, ".agvexa-staging")):
        report.error("%s não é um staging do AG Vexa (falta .agvexa-staging)" % staging)
        return
    cfg_path = os.path.join(staging, "ventoy", "ventoy.json")
    if not os.path.isfile(cfg_path):
        report.error("staging sem ventoy/ventoy.json")
        return
    validate_ventoy_json(cfg_path, staging, report, strict_images=True)
    for t in THEMES:
        validate_theme(os.path.join(staging, "ventoy", "themes", t, "theme.txt"), report, read_version())
    validate_f6(os.path.join(staging, "ventoy", "ventoy_grub.cfg"), report, read_version())
    for folder in EXTRA_FOLDERS:
        if not os.path.isfile(os.path.join(staging, folder, "LEIA-ME.txt")):
            report.error("pasta de apoio sem LEIA-ME: %s" % folder)
    # o Ventoy exige 'ventoy' e 'ventoy.json' em minúsculas
    for name in os.listdir(staging):
        if name.upper() in FORBIDDEN_MEDIA_FOLDERS:
            report.error("pasta %s não pode existir na mídia do toolkit (dados de clientes)" % name)
        if name.lower() == "ventoy" and name != "ventoy":
            report.error("diretório deve ser 'ventoy' em minúsculas, encontrado '%s'" % name)
    sums = os.path.join(staging, "SHA256SUMS-AGVEXA.txt")
    if os.path.isfile(sums):
        bad = 0
        with open(sums, encoding="utf-8") as fh:
            for line in fh:
                digest, name = line.rstrip("\n").split("  ", 1)
                p = os.path.join(staging, name)
                if not os.path.isfile(p):
                    report.error("checksum lista arquivo ausente: %s" % name)
                    bad += 1
                    continue
                if os.path.getsize(p) < 64 * 1024 * 1024:  # ISOs grandes: conferidas por verify-isos
                    h = hashlib.sha256(open(p, "rb").read()).hexdigest()
                    if h != digest:
                        report.error("checksum divergente: %s" % name)
                        bad += 1
        if not bad:
            report.ok("SHA256SUMS-AGVEXA.txt consistente")
    else:
        report.error("staging sem SHA256SUMS-AGVEXA.txt")


# ------------------------------------------------------------------ staging

STAGING_BASE = os.path.join(ROOT, "build")
MARKER = ".agvexa-staging"

# Pastas de apoio usadas com o Windows aberto (fora do menu de boot). O
# conteúdo real fica em extras/<PASTA>/ no projeto (fora do Git) e é levado
# para a raiz da mídia pelo staging. Ver media-layout/<PASTA>/LEIA-ME.txt.
EXTRA_FOLDERS = ("BIOS_FIRMWARE", "DRIVERS", "FERRAMENTAS", "INSTALADORES")
EXTRAS_DIR = os.path.join(ROOT, "extras")
# Dados de clientes nunca vão para a mídia do toolkit (docs/instalacao-segura.md, §10).
FORBIDDEN_MEDIA_FOLDERS = ("CLIENTES",)


def plan_extras(extras_dir):
    """Lista (origem, caminho relativo na mídia) dos arquivos de extras/. Lança ValueError
    se houver pasta proibida (ex.: CLIENTES)."""
    plan, ignored = [], []
    if not os.path.isdir(extras_dir):
        return plan, ignored
    for name in sorted(os.listdir(extras_dir)):
        src_dir = os.path.join(extras_dir, name)
        if not os.path.isdir(src_dir):
            continue
        if name.upper() in FORBIDDEN_MEDIA_FOLDERS:
            raise ValueError("extras/%s não pode ir para a mídia: dados de clientes ficam em partição "
                             "criptografada separada (docs/instalacao-segura.md)" % name)
        if name not in EXTRA_FOLDERS:
            ignored.append(name)
            continue
        for dirpath, dirs, files in os.walk(src_dir):
            dirs[:] = sorted(d for d in dirs if not d.startswith("."))
            for f in sorted(files):
                if f.startswith(".") or f.startswith("._"):
                    continue
                full = os.path.join(dirpath, f)
                plan.append((full, os.path.join(name, os.path.relpath(full, src_dir))))
    return plan, ignored


def safe_staging_dir(path):
    """Garante que o staging é um diretório comum dentro de build/ do projeto."""
    path = os.path.abspath(path)
    if not is_inside(path, STAGING_BASE) or os.path.realpath(path) == os.path.realpath(STAGING_BASE):
        raise ValueError("o staging deve ficar dentro de %s (recebido: %s)" % (rel(STAGING_BASE), path))
    if path.startswith("/dev/") or path.startswith("/proc/") or path.startswith("/sys/"):
        raise ValueError("caminho de sistema não permitido: %s" % path)
    if os.path.islink(path):
        raise ValueError("o staging não pode ser um link simbólico: %s" % path)
    if os.path.exists(path):
        if not os.path.isdir(path):
            raise ValueError("%s existe e não é diretório" % path)
        if os.path.ismount(path):
            raise ValueError("%s é ponto de montagem; o staging deve ser diretório comum" % path)
        if os.listdir(path) and not os.path.isfile(os.path.join(path, MARKER)):
            raise ValueError("%s não está vazio e não é um staging do AG Vexa; nada será apagado" % path)
    return path


def copy_tree(src, dst, actions, dry_run, exclude=()):
    for dirpath, dirs, files in os.walk(src):
        dirs[:] = sorted(d for d in dirs if d not in exclude)
        reldir = os.path.relpath(dirpath, src)
        target_dir = os.path.normpath(os.path.join(dst, reldir))
        for f in sorted(files):
            if f in exclude:
                continue
            s = os.path.join(dirpath, f)
            d = os.path.join(target_dir, f)
            actions.append(("copiar", rel(s), d))
            if not dry_run:
                os.makedirs(target_dir, exist_ok=True)
                shutil.copy2(s, d)


def cmd_stage(args):
    try:
        out = safe_staging_dir(args.output)
    except ValueError as exc:
        print("ERRO: %s" % exc)
        return EXIT_USAGE
    version = read_version()
    categories = load_categories()
    root_iso = categories["raiz_iso"].strip("/")
    actions = []
    dry = args.dry_run
    print("AG Vexa Toolkit %s - preparação de staging%s" % (version, " [DRY-RUN]" if dry else ""))
    print("  destino: %s" % out)
    print("  modo das ISOs: %s" % args.iso_mode)

    # 0) conferir extras/ antes de tocar no staging (recusa CLIENTES etc.)
    try:
        extra_plan, extra_ignored = plan_extras(args.extras)
    except ValueError as exc:
        print("ERRO: %s" % exc)
        return EXIT_ERROR

    # 1) ISOs: só entram as verificadas (ou não verificadas com --allow-unverified)
    images = []
    iso_plan = []
    if args.iso_mode != "none":
        if not os.path.isfile(args.manifest):
            print("ERRO: manifesto não encontrado: %s" % args.manifest)
            print("      Copie catalog/isos-manifest.example.json para catalog/isos-manifest.json e preencha,")
            print("      ou use --iso-mode none para preparar só configuração e documentação.")
            return EXIT_USAGE
        print("\n[1] Verificando ISOs do manifesto")
        library = os.path.abspath(args.library)
        results = verify_isos(args.manifest, library, use_cache=True, quiet=True)
        manifest = load_manifest(args.manifest)
        by_id = {i["id"]: i for i in manifest["itens"]}
        for r in results:
            item = by_id.get(r["id"])
            if item is None:
                continue
            ok = r["status"] == ISO_STATUS_OK or (args.allow_unverified and r["status"] == ISO_STATUS_UNVERIFIED)
            mark = "incluir" if ok else "IGNORAR"
            print("    %-8s %-22s %s" % (mark, r["status"], r["arquivo"]))
            if not ok:
                continue
            media_path = "/%s/%s/%s" % (root_iso, item["categoria"], os.path.basename(item["arquivo"]))
            alias = item["alias_menu"]
            if r["status"] == ISO_STATUS_UNVERIFIED:
                alias += " [NÃO VERIFICADA]"
            images.append({"path": media_path, "alias": alias, "dica1": item.get("dica1"),
                           "dica2": item.get("dica2"), "sha256": r["sha256_calculado"]})
            iso_plan.append((os.path.join(library, item["arquivo"]), os.path.join(out, media_path.lstrip("/"))))
        if not images:
            print("    (nenhuma ISO apta; o menu mostrará apenas o que existir na mídia)")

    # 2) limpeza segura do staging anterior
    print("\n[2] Preparando diretório")
    if os.path.isdir(out) and os.listdir(out):
        actions.append(("limpar", "staging anterior (marcado)", out))
        if not dry:
            shutil.rmtree(out)
    if not dry:
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, MARKER), "w", encoding="utf-8") as fh:
            fh.write("AG Vexa Toolkit %s staging %s\n" % (version, datetime.datetime.now().isoformat(timespec="seconds")))

    # 3) layout base da mídia, temas, menu F6, documentação
    print("[3] Copiando layout, temas, documentação e módulos")
    copy_tree(os.path.join(ROOT, "media-layout"), out, actions, dry)
    copy_tree(os.path.join(ROOT, "ventoy", "themes"), os.path.join(out, "ventoy", "themes"), actions, dry)
    actions.append(("copiar", "ventoy/ventoy_grub.cfg", os.path.join(out, "ventoy", "ventoy_grub.cfg")))
    if not dry:
        shutil.copy2(F6_CFG, os.path.join(out, "ventoy", "ventoy_grub.cfg"))
    for c in categories["categorias"]:
        d = os.path.join(out, root_iso, c["id"])
        actions.append(("criar", "pasta de categoria", d))
        if not dry:
            os.makedirs(d, exist_ok=True)
    extras = [("docs", "AGVexa/docs"), ("templates", "AGVexa/modelos"),
              ("windows-optimizer", "AGVexa/windows-optimizer"), ("catalog", "AGVexa/catalogo")]
    for src, dst in extras:
        copy_tree(os.path.join(ROOT, src), os.path.join(out, dst), actions, dry,
                  exclude=("previews", "isos-manifest.json", "__pycache__"))
    for f in ("VERSION", "CHANGELOG.md"):
        actions.append(("copiar", f, os.path.join(out, "AGVexa", f)))
        if not dry:
            os.makedirs(os.path.join(out, "AGVexa"), exist_ok=True)
            shutil.copy2(os.path.join(ROOT, f), os.path.join(out, "AGVexa", f))

    # 3b) pastas de apoio (drivers, instaladores, ferramentas, BIOS/firmware)
    extra_mode = "copy" if args.iso_mode == "copy" else ("link" if args.iso_mode == "link" else "none")
    print("[3b] Pastas de apoio: %d arquivo(s) de %s (%s)" % (len(extra_plan), rel(args.extras), extra_mode))
    for name in extra_ignored:
        print("    AVISO: extras/%s ignorada (pastas aceitas: %s)" % (name, ", ".join(EXTRA_FOLDERS)))
    if extra_mode != "none":
        for src, relpath in extra_plan:
            dst = os.path.join(out, relpath)
            actions.append((extra_mode, rel(src), dst))
            if dry:
                continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.lexists(dst):   # ex.: INVENTARIO.csv real substitui o modelo vazio
                os.remove(dst)
            if extra_mode == "copy":
                shutil.copy2(src, dst)
            else:
                os.symlink(os.path.realpath(src), dst)

    # 4) ISOs
    print("[4] ISOs (%s)" % args.iso_mode)
    for src, dst in iso_plan:
        actions.append((args.iso_mode, rel(src), dst))
        if dry:
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if args.iso_mode == "copy":
            shutil.copy2(src, dst)
        elif args.iso_mode == "link":
            os.symlink(os.path.realpath(src), dst)

    # 5) ventoy.json final (apenas imagens realmente presentes)
    print("[5] Gerando ventoy/ventoy.json do staging (%d imagens)" % len(images))
    config = build_ventoy_config(categories, images, ascii_only=args.ascii_menu)
    actions.append(("gerar", "ventoy.json", os.path.join(out, "ventoy", "ventoy.json")))
    if not dry:
        os.makedirs(os.path.join(out, "ventoy"), exist_ok=True)
        with open(os.path.join(out, "ventoy", "ventoy.json"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(dump_json(config))

    # 6) checksums de tudo o que irá para o HD (sha das ISOs vem da verificação)
    print("[6] Gerando SHA256SUMS-AGVEXA.txt")
    iso_sha = {img["path"].lstrip("/"): img["sha256"] for img in images}
    if not dry:
        lines = []
        hash_cache = {}
        for dirpath, dirs, files in os.walk(out):
            dirs.sort()
            for f in sorted(files):
                p = os.path.join(dirpath, f)
                name = os.path.relpath(p, out).replace(os.sep, "/")
                if name in (MARKER, "SHA256SUMS-AGVEXA.txt"):
                    continue
                digest = iso_sha.get(name)
                if digest is None:
                    digest, _ = sha256_file(p, hash_cache)
                lines.append("%s  %s\n" % (digest, name))
        with open(os.path.join(out, "SHA256SUMS-AGVEXA.txt"), "w", encoding="utf-8", newline="\n") as fh:
            fh.writelines(lines)

    print("\nResumo: %d ações%s" % (len(actions), " planejadas (nada foi gravado)" if dry else ""))
    if args.verbose or dry:
        for act, src, dst in actions[: (None if args.verbose else 40)]:
            print("  %-7s %s -> %s" % (act, src, rel(dst)))
        if not args.verbose and len(actions) > 40:
            print("  ... (%d ações a mais; use --verbose)" % (len(actions) - 40))
    if not dry:
        print("\nStaging pronto em %s" % rel(out))
        print("Próximo passo: scripts/validate-config.sh --staging %s" % rel(out))
        if args.iso_mode == "link":
            print("Atenção: ISOs e arquivos de extras/ são links simbólicos. Ao copiar para o HD (exFAT), use cópia que")
            print("siga links (ex.: rsync -rL ou cp -rL). Veja docs/instalacao-segura.md.")
    return EXIT_OK


# ------------------------------------------------------------------ CLI

def main(argv=None):
    ap = argparse.ArgumentParser(prog="agvexa.py", description="Biblioteca do AG Vexa Toolkit")
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("build-base", help="gera ventoy/ventoy.json a partir das categorias")
    p.add_argument("--check", action="store_true", help="só compara, não grava")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_build_base)

    p = sub.add_parser("validate", help="valida configuração, temas e catálogo")
    p.add_argument("--staging", help="também valida um diretório de staging")
    p.add_argument("--quiet", action="store_true")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("verify-isos", help="verifica ISOs contra o manifesto")
    p.add_argument("--manifest", default=os.path.join(ROOT, "catalog", "isos-manifest.json"))
    p.add_argument("--library", default=os.path.join(ROOT, "isos"))
    p.add_argument("--report-dir", default=os.path.join(ROOT, "reports"))
    p.add_argument("--no-cache", action="store_true")
    p.add_argument("--quiet", action="store_true")
    p.set_defaults(func=cmd_verify_isos)

    p = sub.add_parser("stage", help="monta o staging em build/")
    p.add_argument("--output", default=os.path.join(STAGING_BASE, "staging"))
    p.add_argument("--manifest", default=os.path.join(ROOT, "catalog", "isos-manifest.json"))
    p.add_argument("--library", default=os.path.join(ROOT, "isos"))
    p.add_argument("--iso-mode", choices=("link", "copy", "none"), default="link")
    p.add_argument("--extras", default=EXTRAS_DIR)
    p.add_argument("--allow-unverified", action="store_true")
    p.add_argument("--ascii-menu", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--verbose", action="store_true")
    p.set_defaults(func=cmd_stage)

    args = ap.parse_args(argv)
    if not getattr(args, "func", None):
        ap.print_help()
        return EXIT_USAGE
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
