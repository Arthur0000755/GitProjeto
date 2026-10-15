#!/usr/bin/env python3
"""Gera as imagens do tema GRUB/Ventoy do AG Vexa Toolkit.

Saídas (todas determinísticas, sem aleatoriedade):
  ventoy/themes/agvexa/        fundo, molduras (9 partes), barra de rolagem,
                               caixa de terminal e ícones 24x24
  ventoy/themes/agvexa-lite/   apenas destaque de seleção e ícones
  branding/backgrounds/        papéis de parede 1024x768 e 1920x1080
  branding/icons/              ícones-mestre 96x96
  docs/previews/               pré-visualizações APROXIMADAS (não são capturas
                               do GRUB; servem apenas para revisão visual)

Requisitos: Python 3.8+ e Pillow (python3-pil). Não acessa rede nem
dispositivos; escreve somente dentro do diretório do projeto.

Os arquivos theme.txt NÃO são gerados aqui: são escritos à mão e
validados por scripts/lib/agvexa_validate.py.
"""

import argparse
import json
import os
import sys

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
except ImportError:  # pragma: no cover - depende do ambiente
    sys.stderr.write("ERRO: Pillow não encontrado. Instale python3-pil (requer autorização) "
                     "ou use as imagens já versionadas.\n")
    sys.exit(3)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PALETTE = json.load(open(os.path.join(ROOT, "branding", "palette.json"), encoding="utf-8"))
FONTS = os.path.join(ROOT, "branding", "fonts")
VERSION = open(os.path.join(ROOT, "VERSION"), encoding="utf-8").read().strip()

THEME = os.path.join(ROOT, "ventoy", "themes", "agvexa")
THEME_LITE = os.path.join(ROOT, "ventoy", "themes", "agvexa-lite")
OFFICIAL_LOGO = os.path.join(ROOT, "branding", "logo-placeholder", "logo-oficial.png")

# Categorias do menu: classe -> ícone. Mantido em sincronia com
# catalog/categorias.json (verificado pelos testes).
ICON_CLASSES = [
    "agv-instalacao", "agv-hardware", "agv-discos", "agv-backup", "agv-linux",
    "agv-avancado", "agv-info", "agv-seguranca", "agv-energia", "agv-reiniciar",
    "vtoydir", "vtoyret", "vtoyiso", "vtoywim", "vtoyefi", "vtoyimg", "vtoyvhd", "vtoyvtoy",
]


def rgb(hexstr, alpha=255):
    hexstr = hexstr.lstrip("#")
    return tuple(int(hexstr[i:i + 2], 16) for i in (0, 2, 4)) + (alpha,)


def font(name, size):
    """Carrega fonte versionada em branding/fonts com fallback seguro."""
    candidates = {
        "bold": ["Inter-Bold.otf"],
        "semibold": ["Inter-SemiBold.otf", "Inter-Bold.otf"],
        "regular": ["Inter-Regular.otf"],
        "mono": ["DejaVuSansMono.ttf"],
    }[name]
    for c in candidates:
        path = os.path.join(FONTS, c)
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def save_png(img, path):
    """Salva PNG compatível com o leitor do GRUB: 8 bits, RGB/RGBA, sem entrelaçamento."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA")
    img.save(path, "PNG", optimize=True)


def spaced(draw, xy, text, fnt, fill, tracking=0):
    """Desenha texto com espaçamento entre letras (tracking em px)."""
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += draw.textlength(ch, font=fnt) + tracking
    return x


def text_width(draw, text, fnt, tracking=0):
    return sum(draw.textlength(ch, font=fnt) + tracking for ch in text) - tracking


# ---------------------------------------------------------------- fundo

def background(w, h, with_panel=True):
    s = w / 1024.0  # fator de escala relativo ao desenho base 1024x768
    img = Image.new("RGBA", (w, h), rgb(PALETTE["fundo_principal"]))
    px = img.load()
    top = rgb(PALETTE["fundo_principal"])
    bottom = rgb("#0E1729")
    for y in range(h):
        t = y / max(1, h - 1)
        row = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)) + (255,)
        for x in range(w):
            px[x, y] = row

    # brilho azul discreto no canto superior direito
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    cx, cy, r = int(w * 0.92), int(-h * 0.08), int(w * 0.45)
    gd.ellipse((cx - r, cy - r, cx + r, cy + r), fill=rgb(PALETTE["azul_secundario"], 70))
    glow = glow.filter(ImageFilter.GaussianBlur(int(120 * s)))
    img = Image.alpha_composite(img, glow)

    # grade de pontos muito sutil
    dots = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dd = ImageDraw.Draw(dots)
    step = max(16, int(24 * s))
    for y in range(step, h, step):
        for x in range(step, w, step):
            dd.point((x, y), fill=rgb("#1E293B", 150))
    img = Image.alpha_composite(img, dots)

    d = ImageDraw.Draw(img)
    m = int(56 * s)

    # cabeçalho: identificação tipográfica (ou logo oficial, se fornecida)
    y = int(40 * s)
    if os.path.exists(OFFICIAL_LOGO):
        logo = Image.open(OFFICIAL_LOGO).convert("RGBA")
        lh = int(28 * s)
        logo = logo.resize((max(1, int(logo.width * lh / logo.height)), lh), Image.LANCZOS)
        img.alpha_composite(logo, (m, y))
        d = ImageDraw.Draw(img)
    else:
        spaced(d, (m, y), "AG VEXA", font("semibold", int(14 * s)), rgb(PALETTE["azul_destaque"]), int(4 * s))
        spaced(d, (m + text_width(d, "AG VEXA", font("semibold", int(14 * s)), int(4 * s)) + int(14 * s), y),
               "ASSISTÊNCIA TÉCNICA", font("regular", int(14 * s)), rgb(PALETTE["texto_secundario"]), int(2 * s))
    y += int(26 * s)
    d.text((m - int(2 * s), y), "AG VEXA TOOLKIT", font=font("bold", int(42 * s)), fill=rgb(PALETTE["texto_principal"]))
    y += int(56 * s)
    spaced(d, (m, y), "DIAGNÓSTICO  •  MANUTENÇÃO  •  RECUPERAÇÃO", font("semibold", int(14 * s)),
           rgb(PALETTE["azul_destaque"]), int(2 * s))
    y += int(30 * s)
    # filete de destaque em degradê
    for i in range(int(140 * s)):
        t = i / (140 * s)
        c = tuple(int(rgb(PALETTE["azul_destaque"])[k] * (1 - t) + rgb(PALETTE["azul_secundario"])[k] * t) for k in range(3))
        d.line((m + i, y, m + i, y + max(2, int(3 * s))), fill=c + (255,))

    if with_panel:
        # painel "Como usar" à direita do menu
        x0, y0, x1, y1 = int(700 * s), int(200 * s), int(968 * s), int(622 * s)
        d.rounded_rectangle((x0, y0, x1, y1), radius=int(10 * s), fill=rgb(PALETTE["fundo_painel"], 235),
                            outline=rgb(PALETTE["borda"]), width=max(1, int(s)))
        tx = x0 + int(20 * s)
        ty = y0 + int(18 * s)
        h1 = font("semibold", int(12 * s))
        body = font("regular", int(13 * s))
        key = font("semibold", int(13 * s))
        spaced(d, (tx, ty), "COMO USAR", h1, rgb(PALETTE["azul_destaque"]), int(2 * s))
        ty += int(28 * s)
        for k, v in [("↑ ↓", "Navegar"), ("Enter", "Abrir / iniciar"), ("Esc", "Voltar"),
                     ("F4", "Iniciar disco local"), ("F5", "Ferramentas / modo texto"),
                     ("F6", "Informações do Toolkit")]:
            d.rounded_rectangle((tx, ty - int(2 * s), tx + int(52 * s), ty + int(20 * s)), radius=int(4 * s),
                                fill=rgb(PALETTE["fundo_secundario"]), outline=rgb(PALETTE["borda_suave"]))
            kw = d.textlength(k, font=key)
            d.text((tx + (int(52 * s) - kw) / 2, ty), k, font=key, fill=rgb(PALETTE["texto_principal"]))
            d.text((tx + int(64 * s), ty), v, font=body, fill=rgb(PALETTE["texto_menu"]))
            ty += int(30 * s)
        ty += int(12 * s)
        d.line((tx, ty, x1 - int(20 * s), ty), fill=rgb(PALETTE["borda_suave"]), width=max(1, int(s)))
        ty += int(18 * s)
        spaced(d, (tx, ty), "ANTES DE QUALQUER REPARO", h1, rgb(PALETTE["alerta"]), int(2 * s))
        ty += int(26 * s)
        for line in ["Autorização do proprietário", "Backup antes de alterar discos",
                     "Confirme origem e destino", "Prefira testes somente leitura"]:
            d.ellipse((tx, ty + int(6 * s), tx + int(5 * s), ty + int(11 * s)), fill=rgb(PALETTE["alerta"]))
            d.text((tx + int(14 * s), ty), line, font=body, fill=rgb(PALETTE["texto_menu"]))
            ty += int(24 * s)

    # rodapé
    fy = h - int(48 * s)
    d.line((m, fy, w - m, fy), fill=rgb(PALETTE["borda_suave"]), width=max(1, int(s)))
    d.text((m, fy + int(12 * s)), "AG Vexa — Assistência Técnica", font=font("regular", int(13 * s)),
           fill=rgb(PALETTE["texto_secundario"]))
    return img.convert("RGB")


# ---------------------------------------------------------------- 9 partes

def nine_slice(prefix, outdir, size, radius, fill, border=None, accent=None, accent_w=0):
    """Gera as 9 partes de uma moldura no padrão GRUB: prefix_{nw,n,ne,w,c,e,sw,s,se}.png."""
    big = 4  # supersampling para cantos suaves
    full = size * 3
    canvas = Image.new("RGBA", (full * big, full * big), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle((0, 0, full * big - 1, full * big - 1), radius=radius * big, fill=fill,
                        outline=border, width=big if border else 0)
    if accent:
        d.rounded_rectangle((0, 0, accent_w * big, full * big - 1), radius=min(radius, accent_w) * big, fill=accent)
    canvas = canvas.resize((full, full), Image.LANCZOS)
    parts = {"nw": (0, 0), "n": (1, 0), "ne": (2, 0), "w": (0, 1), "c": (1, 1),
             "e": (2, 1), "sw": (0, 2), "s": (1, 2), "se": (2, 2)}
    for name, (cx, cy) in parts.items():
        tile = canvas.crop((cx * size, cy * size, (cx + 1) * size, (cy + 1) * size))
        save_png(tile, os.path.join(outdir, "%s_%s.png" % (prefix, name)))


def slider(outdir):
    for name, h in (("n", 3), ("c", 4), ("s", 3)):
        img = Image.new("RGBA", (6, h), rgb(PALETTE["azul_destaque"], 200))
        save_png(img, os.path.join(outdir, "slider_%s.png" % name))


# ---------------------------------------------------------------- ícones

def draw_icon(cls, size=96):
    s = size / 96.0
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = rgb(PALETTE["azul_icone"])
    a = rgb(PALETTE["azul_destaque"])
    w = max(2, int(7 * s))

    def box(x0, y0, x1, y1, r=8, fill=None, outline=c, width=w):
        d.rounded_rectangle((x0 * s, y0 * s, x1 * s, y1 * s), radius=r * s, fill=fill, outline=outline, width=width)

    def line(*pts, color=c, width=w):
        d.line([(p[0] * s, p[1] * s) for p in pts], fill=color, width=width, joint="curve")

    def circle(cx, cy, r, fill=None, outline=c, width=w):
        d.ellipse(((cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s), fill=fill, outline=outline, width=width)

    if cls == "agv-instalacao":            # monitor com seta de instalação
        box(10, 14, 86, 66)
        line((48, 66), (48, 80)); line((30, 82), (66, 82))
        line((48, 24), (48, 52), color=a); line((36, 42), (48, 54), (60, 42), color=a)
    elif cls == "agv-hardware" or cls == "vtoyefi":   # chip
        box(24, 24, 72, 72)
        box(38, 38, 58, 58, r=3, fill=a, outline=a)
        for p in (34, 48, 62):
            line((p, 10), (p, 24)); line((p, 72), (p, 86)); line((10, p), (24, p)); line((72, p), (86, p))
    elif cls in ("agv-discos", "vtoyimg", "vtoyvhd"):  # disco rígido
        box(12, 18, 84, 78, r=10)
        circle(48, 44, 16)
        circle(48, 44, 3, fill=a, outline=a)
        line((22, 68), (74, 68), width=max(1, int(4 * s)))
        circle(74, 68, 2, fill=a, outline=a)
    elif cls == "agv-backup":               # caixa de arquivo com seta para cima
        box(14, 40, 82, 82, r=6)
        line((14, 52), (82, 52))
        line((48, 12), (48, 40), color=a); line((36, 24), (48, 12), (60, 24), color=a)
    elif cls == "agv-linux":                # terminal >_
        box(10, 16, 86, 80)
        line((24, 36), (38, 48), (24, 60), color=a)
        line((44, 62), (66, 62))
    elif cls == "agv-avancado":             # chave inglesa estilizada
        circle(34, 34, 18)
        d.rectangle((26 * s, 8 * s, 42 * s, 26 * s), fill=(0, 0, 0, 0))
        line((46, 46), (82, 82), width=int(12 * s))
        circle(34, 34, 4, fill=a, outline=a)
    elif cls == "agv-info":
        circle(48, 48, 36)
        circle(48, 30, 4, fill=a, outline=a)
        line((48, 44), (48, 68), color=a)
    elif cls == "agv-seguranca":            # escudo
        pts = [(48, 10), (80, 22), (76, 54), (48, 86), (20, 54), (16, 22), (48, 10)]
        line(*pts)
        line((34, 48), (44, 58), (62, 38), color=a)
    elif cls == "agv-energia":              # símbolo de energia
        d.arc((18 * s, 18 * s, 78 * s, 78 * s), start=-60, end=240, fill=c, width=w)
        line((48, 10), (48, 46), color=a)
    elif cls == "agv-reiniciar":            # seta circular
        d.arc((18 * s, 18 * s, 78 * s, 78 * s), start=-30, end=270, fill=c, width=w)
        line((48, 6), (62, 18), (48, 30), color=a)
    elif cls == "vtoydir":                  # pasta
        line((10, 26), (36, 26), (44, 34), (86, 34), (86, 78), (10, 78), (10, 26))
    elif cls == "vtoyret":                  # seta para trás
        line((80, 48), (18, 48)); line((38, 28), (18, 48), (38, 68))
    else:                                   # vtoyiso / vtoywim / vtoyvtoy: disco óptico
        circle(48, 48, 36)
        circle(48, 48, 10, outline=a)
    return img


def icons(outdir, size):
    for cls in ICON_CLASSES:
        big = draw_icon(cls, 96 * 4 if size < 96 else 96)
        img = big.resize((size, size), Image.LANCZOS) if big.width != size else big
        save_png(img, os.path.join(outdir, cls + ".png"))


# ---------------------------------------------------------------- prévia

PREVIEW_ITEMS = [
    ("agv-instalacao", "01 — Instalação de Sistemas"),
    ("agv-hardware", "02 — Diagnóstico de Hardware"),
    ("agv-discos", "03 — Manutenção de Discos"),
    ("agv-backup", "04 — Backup e Recuperação"),
    ("agv-linux", "05 — Ambientes Linux Live"),
    ("agv-avancado", "06 — Ferramentas Avançadas"),
]


def preview(theme_dir, lite, out):
    """Composição APROXIMADA do menu para revisão visual (fonte e métricas do GRUB diferem)."""
    W, H = 1024, 768
    if lite:
        img = Image.new("RGBA", (W, H), rgb(PALETTE["fundo_principal"]))
        d = ImageDraw.Draw(img)
        d.text((int(W * 0.055), int(H * 0.06)), "AG VEXA TOOLKIT — modo leve", font=font("mono", 16),
               fill=rgb(PALETTE["texto_principal"]))
    else:
        img = Image.open(os.path.join(theme_dir, "background.png")).convert("RGBA")
        d = ImageDraw.Draw(img)
    mx, my, mw, mh = int(W * 0.055), int(H * 0.26), int(W * 0.605), int(H * 0.55)
    if not lite:
        d.rounded_rectangle((mx, my, mx + mw, my + mh), radius=8, fill=rgb(PALETTE["fundo_secundario"], 235),
                            outline=rgb(PALETTE["borda"]))
    mono = font("mono", 15)
    iy = my + 14
    for i, (cls, label) in enumerate(PREVIEW_ITEMS):
        if i == 0:
            d.rounded_rectangle((mx + 10, iy - 2, mx + mw - 10, iy + 34), radius=6, fill=rgb(PALETTE["azul_secundario"]))
            d.rectangle((mx + 10, iy - 2, mx + 14, iy + 34), fill=rgb(PALETTE["azul_destaque"]))
        ico = Image.open(os.path.join(theme_dir, "icons", cls + ".png")).convert("RGBA")
        img.alpha_composite(ico, (mx + 24, iy + 4))
        d.text((mx + 60, iy + 7), label, font=mono,
               fill=rgb(PALETTE["texto_principal"] if i == 0 else PALETTE["texto_menu"]))
        iy += 40
    d.text((mx, int(H * 0.835)), "Instaladores oficiais de sistemas. Use somente ISOs verificadas.",
           font=mono, fill=rgb(PALETTE["texto_secundario"]))
    d.text((mx, int(H * 0.90)), "L:Idioma  F1:Ajuda  F2:Explorar  F3:Visualizacao em Lista  F4  F5  F6",
           font=font("mono", 13), fill=rgb(PALETTE["texto_secundario"]))
    d.text((int(W * 0.62), int(H * 0.95)), "Toolkit %s  |  Ventoy x.y.z" % VERSION, font=font("mono", 13),
           fill=rgb(PALETTE["texto_secundario"]))
    # faixa de aviso: deixar claro que é uma simulação
    d.rectangle((0, 0, W, 18), fill=rgb(PALETTE["alerta"]))
    d.text((8, 2), "PRÉ-VISUALIZAÇÃO APROXIMADA (Pillow) — não é captura real do GRUB/Ventoy",
           font=font("semibold", 12), fill=rgb("#111111"))
    save_png(img.convert("RGB"), out)


# ---------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="apenas lista o que seria gerado")
    ap.add_argument("--no-preview", action="store_true", help="não gera as pré-visualizações em docs/previews")
    args = ap.parse_args(argv)

    plan = [
        "ventoy/themes/agvexa/background.png (1024x768)",
        "ventoy/themes/agvexa/menu_*.png, select_*.png, terminal_box_*.png, slider_*.png",
        "ventoy/themes/agvexa/icons/*.png (24x24, %d classes)" % len(ICON_CLASSES),
        "ventoy/themes/agvexa-lite/select_*.png e icons/*.png",
        "branding/backgrounds/agvexa-1024x768.png, agvexa-1920x1080.png",
        "branding/icons/*.png (96x96)",
    ]
    if not args.no_preview:
        plan.append("docs/previews/preview-agvexa.png, preview-agvexa-lite.png (aproximadas)")
    if args.dry_run:
        print("[dry-run] Seriam gerados:")
        for p in plan:
            print("  - " + p)
        return 0

    bg = background(1024, 768)
    save_png(bg, os.path.join(THEME, "background.png"))
    save_png(bg, os.path.join(ROOT, "branding", "backgrounds", "agvexa-1024x768.png"))
    save_png(background(1920, 1080), os.path.join(ROOT, "branding", "backgrounds", "agvexa-1920x1080.png"))

    nine_slice("menu", THEME, 12, 10, rgb(PALETTE["fundo_secundario"], 232), border=rgb(PALETTE["borda"]))
    nine_slice("terminal_box", THEME, 8, 6, rgb(PALETTE["fundo_principal"], 250), border=rgb(PALETTE["borda"]))
    for target in (THEME, THEME_LITE):
        nine_slice("select", target, 6, 5, rgb(PALETTE["azul_secundario"]),
                   accent=rgb(PALETTE["azul_destaque"]), accent_w=3)
        icons(os.path.join(target, "icons"), 24)
    slider(THEME)
    icons(os.path.join(ROOT, "branding", "icons"), 96)

    if not args.no_preview:
        preview(THEME, False, os.path.join(ROOT, "docs", "previews", "preview-agvexa.png"))
        preview(THEME_LITE, True, os.path.join(ROOT, "docs", "previews", "preview-agvexa-lite.png"))

    for p in plan:
        print("gerado: " + p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
