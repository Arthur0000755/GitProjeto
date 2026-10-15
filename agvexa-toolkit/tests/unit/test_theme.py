"""Testes do validador de temas GRUB e do menu F6."""
import os
import shutil
import struct
import tempfile
import unittest
import zlib

from tests.unit.helpers import ROOT, agvexa, quiet_report


def png_bytes(w=2, h=2, depth=8, ctype=6, interlace=0):
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", w, h, depth, ctype, 0, 0, interlace)
    bpp = {6: 4, 2: 3, 0: 1, 4: 2}.get(ctype, 4) * (depth // 8 or 1)
    raw = b"".join(b"\x00" + b"\x00" * (w * bpp) for _ in range(h))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


class ThemeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="agv-theme-")
        self.version = agvexa.read_version()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def theme(self, text, files=()):
        for name, data in files:
            p = os.path.join(self.tmp, name)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "wb") as fh:
                fh.write(data)
        path = os.path.join(self.tmp, "theme.txt")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        r = quiet_report()
        agvexa.validate_theme(path, r, None)
        return r

    def test_project_themes_are_valid(self):
        for t in agvexa.THEMES:
            r = quiet_report()
            agvexa.validate_theme(os.path.join(ROOT, "ventoy", "themes", t, "theme.txt"), r, self.version)
            self.assertEqual(r.errors, [], t)

    def test_project_themes_show_current_version(self):
        for t in agvexa.THEMES:
            with open(os.path.join(ROOT, "ventoy", "themes", t, "theme.txt"), encoding="utf-8") as fh:
                self.assertIn("Toolkit %s" % self.version, fh.read())

    def test_parse_nested_components(self):
        g, comps, errs = agvexa.parse_theme('title-text: "A"\n+ hbox { left = 30%+200\n + label { text = "x" } }\n')
        self.assertEqual(errs, [])
        self.assertEqual(g["title-text"], "A")
        self.assertEqual(comps[0]["props"]["left"], "30%+200")
        self.assertEqual(comps[0]["children"][0]["type"], "label")

    def test_minimal_valid_theme(self):
        r = self.theme('desktop-color: "#0B1220"\n+ boot_menu { left = 10% top = 10% width = 80% height = 80% }\n')
        self.assertEqual(r.errors, [])

    def test_missing_boot_menu(self):
        self.assertTrue(self.theme('desktop-color: "#000000"\n').errors)

    def test_unbalanced_braces(self):
        self.assertTrue(self.theme('+ boot_menu { left = 1%\n').errors)

    def test_unknown_global_property(self):
        self.assertTrue(self.theme('desktop-colour: "#000000"\n+ boot_menu { }\n').errors)

    def test_unknown_component_property(self):
        self.assertTrue(self.theme('+ boot_menu { item_colour = "#fff" }\n').errors)

    def test_invalid_color(self):
        self.assertTrue(self.theme('+ boot_menu { item_color = "#12345" }\n').errors)

    def test_missing_desktop_image(self):
        self.assertTrue(self.theme('desktop-image: "bg.png"\n+ boot_menu { }\n').errors)

    def test_missing_pixmap_style(self):
        self.assertTrue(self.theme('+ boot_menu { menu_pixmap_style = "menu_*.png" }\n').errors)

    def test_valid_png_accepted(self):
        r = self.theme('desktop-image: "bg.png"\n+ boot_menu { }\n', [("bg.png", png_bytes())])
        self.assertEqual(r.errors, [])

    def test_interlaced_png_rejected(self):
        r = self.theme('desktop-image: "bg.png"\n+ boot_menu { }\n', [("bg.png", png_bytes(interlace=1))])
        self.assertTrue(r.errors)

    def test_16bit_png_rejected(self):
        r = self.theme('desktop-image: "bg.png"\n+ boot_menu { }\n', [("bg.png", png_bytes(depth=16))])
        self.assertTrue(r.errors)

    def test_palette_png_rejected(self):
        r = self.theme('desktop-image: "bg.png"\n+ boot_menu { }\n', [("bg.png", png_bytes(ctype=3))])
        self.assertTrue(r.errors)

    def test_not_png_rejected(self):
        r = self.theme('desktop-image: "bg.png"\n+ boot_menu { }\n', [("bg.png", b"JFIF....")])
        self.assertTrue(r.errors)

    def test_version_label_required(self):
        path = os.path.join(self.tmp, "theme.txt")
        with open(path, "w") as fh:
            fh.write('+ boot_menu { }\n+ label { text = "Toolkit 9.9.9" }\n')
        r = quiet_report()
        agvexa.validate_theme(path, r, "0.0.1")
        self.assertTrue(r.errors)

    def test_icons_exist_for_all_classes(self):
        cats = agvexa.load_categories()["categorias"]
        classes = {c["classe"] for c in cats} | agvexa.VENTOY_BUILTIN_CLASSES | {
            "agv-info", "agv-seguranca", "agv-energia", "agv-reiniciar", "agv-hardware"}
        for t in agvexa.THEMES:
            for cls in classes:
                self.assertTrue(os.path.isfile(os.path.join(ROOT, "ventoy", "themes", t, "icons", cls + ".png")),
                                "%s sem ícone %s" % (t, cls))


class F6MenuTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="agv-f6-")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def check(self, text, version=None):
        p = os.path.join(self.tmp, "ventoy_grub.cfg")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        r = quiet_report()
        agvexa.validate_f6(p, r, version)
        return r

    def test_project_f6_menu_valid(self):
        r = quiet_report()
        agvexa.validate_f6(agvexa.F6_CFG, r, agvexa.read_version())
        self.assertEqual(r.errors, [])

    def test_f6_classes_have_icons(self):
        import re
        with open(agvexa.F6_CFG, encoding="utf-8") as fh:
            classes = set(re.findall(r"--class=([\w-]+)", fh.read()))
        for t in agvexa.THEMES:
            for c in classes:
                self.assertTrue(os.path.isfile(os.path.join(ROOT, "ventoy", "themes", t, "icons", c + ".png")), c)

    def test_boot_commands_forbidden(self):
        r = self.check("menuentry 'x' {\n    linux /vmlinuz\n    chainloader /efi/boot.efi\n}\n")
        self.assertEqual(len(r.errors), 2)

    def test_unbalanced(self):
        self.assertTrue(self.check("menuentry 'x' {\n    echo 'a'\n").errors)

    def test_braces_inside_strings_ignored(self):
        self.assertEqual(self.check("menuentry 'x {' {\n    echo '}}'\n}\n").errors, [])

    def test_version_required(self):
        self.assertTrue(self.check("menuentry 'x' {\n echo 'v1'\n}\n", version="0.9.9").errors)


if __name__ == "__main__":
    unittest.main()
