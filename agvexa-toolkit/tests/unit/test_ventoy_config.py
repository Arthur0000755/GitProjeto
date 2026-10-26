"""Testes da geração e validação do ventoy.json."""
import json
import os
import shutil
import tempfile
import unittest

from tests.unit.helpers import ROOT, agvexa, quiet_report


def write_cfg(tmp, cfg, raw=None):
    path = os.path.join(tmp, "ventoy.json")
    with open(path, "wb") as fh:
        fh.write(raw if raw is not None else json.dumps(cfg, ensure_ascii=False).encode("utf-8"))
    return path


class VentoyConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="agv-test-")
        self.base = agvexa.build_ventoy_config(agvexa.load_categories())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def validate(self, cfg=None, raw=None):
        r = quiet_report()
        agvexa.validate_ventoy_json(write_cfg(self.tmp, cfg, raw), None, r, theme_root=ROOT)
        return r

    def test_committed_matches_generated(self):
        with open(agvexa.VENTOY_JSON, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), agvexa.dump_json(self.base))

    def test_base_config_is_valid(self):
        r = self.validate(self.base)
        self.assertEqual(r.errors, [])

    def test_utf8_written_without_escapes(self):
        text = agvexa.dump_json(self.base)
        self.assertIn("Instalação", text)
        self.assertNotIn("\\u", text)

    def test_every_category_has_alias_class_tip(self):
        cats = agvexa.load_categories()["categorias"]
        dirs_alias = {a["dir"] for a in self.base["menu_alias"] if "dir" in a}
        dirs_tip = {t["dir"] for t in self.base["menu_tip"]["tips"] if "dir" in t}
        parents = {c["parent"] for c in self.base["menu_class"] if "parent" in c}
        for c in cats:
            d = "/ISO/" + c["id"]
            self.assertIn(d, dirs_alias)
            self.assertIn(d, dirs_tip)
            self.assertIn(d, parents)

    def test_safety_policy_defaults(self):
        control = {k: v for e in self.base["control"] for k, v in e.items()}
        self.assertNotIn("VTOY_MENU_TIMEOUT", control)
        self.assertNotIn("VTOY_DEFAULT_IMAGE", control)
        self.assertEqual(control["VTOY_WIN11_BYPASS_CHECK"], "0")
        self.assertEqual(control["VTOY_WIN11_BYPASS_NRO"], "0")
        self.assertEqual(control["VTOY_SECURE_BOOT_POLICY"], "1")
        self.assertEqual(control["VTOY_MENU_LANGUAGE"], "pt_BR")

    def test_bom_rejected(self):
        raw = b"\xef\xbb\xbf" + json.dumps(self.base).encode()
        self.assertTrue(self.validate(raw=raw).errors)

    def test_invalid_json_rejected(self):
        self.assertTrue(self.validate(raw=b"{ \"control\": [ }").errors)

    def test_unknown_control_option_rejected(self):
        cfg = dict(self.base, control=[{"VTOY_INVENTADA": "1"}])
        self.assertTrue(any("não documentada" in e for e in self.validate(cfg).errors))

    def test_out_of_range_value_rejected(self):
        cfg = dict(self.base, control=[{"VTOY_DEFAULT_MENU_MODE": "2"}])
        self.assertTrue(self.validate(cfg).errors)

    def test_non_string_value_rejected(self):
        cfg = dict(self.base, control=[{"VTOY_DEFAULT_MENU_MODE": 1}])
        self.assertTrue(self.validate(cfg).errors)

    def test_auto_boot_forbidden(self):
        cfg = dict(self.base, control=self.base["control"] + [{"VTOY_MENU_TIMEOUT": "10"}])
        self.assertTrue(any("POLÍTICA" in e for e in self.validate(cfg).errors))

    def test_win11_bypass_forbidden(self):
        cfg = dict(self.base, control=[{"VTOY_WIN11_BYPASS_CHECK": "1"}])
        self.assertTrue(any("POLÍTICA" in e for e in self.validate(cfg).errors))

    def test_unknown_plugin_rejected(self):
        cfg = dict(self.base, plugin_inventado={})
        self.assertTrue(self.validate(cfg).errors)

    def test_relative_alias_path_rejected(self):
        cfg = dict(self.base, menu_alias=[{"dir": "ISO/01", "alias": "x"}])
        self.assertTrue(self.validate(cfg).errors)

    def test_trailing_slash_rejected(self):
        cfg = dict(self.base, menu_alias=[{"dir": "/ISO/01/", "alias": "x"}])
        self.assertTrue(self.validate(cfg).errors)

    def test_menu_tip_decimal_position_rejected(self):
        cfg = dict(self.base, menu_tip=dict(self.base["menu_tip"], left="5.5%"))
        self.assertTrue(any("menu_tip.left" in e for e in self.validate(cfg).errors))

    def test_alias_too_long_rejected(self):
        cfg = dict(self.base, menu_alias=[{"dir": "/ISO/x", "alias": "é" * 200}])
        self.assertTrue(self.validate(cfg).errors)

    def test_missing_theme_file_rejected(self):
        cfg = json.loads(json.dumps(self.base))
        cfg["theme"]["file"].append("/ventoy/themes/nao-existe/theme.txt")
        self.assertTrue(self.validate(cfg).errors)

    def test_default_file_out_of_range(self):
        cfg = json.loads(json.dumps(self.base))
        cfg["theme"]["default_file"] = 5
        self.assertTrue(self.validate(cfg).errors)

    def test_menu_class_requires_single_key(self):
        cfg = dict(self.base, menu_class=[{"dir": "/ISO/a", "parent": "/ISO/a", "class": "x"}])
        self.assertTrue(self.validate(cfg).errors)

    def test_ascii_menu(self):
        self.assertEqual(agvexa.ascii_menu("01 — Instalação"), "01 - Instalacao")
        cfg = agvexa.build_ventoy_config(agvexa.load_categories(), ascii_only=True)
        text = agvexa.dump_json(cfg)
        aliases = [a["alias"] for a in cfg["menu_alias"]]
        self.assertTrue(all(a.isascii() for a in aliases))
        self.assertIn("Instalacao", text)

    def test_images_added_to_alias_and_tips(self):
        imgs = [{"path": "/ISO/02-diagnostico-hardware/mt.iso", "alias": "MemTest86+", "dica1": "a", "dica2": "b"}]
        cfg = agvexa.build_ventoy_config(agvexa.load_categories(), imgs)
        self.assertIn({"image": imgs[0]["path"], "alias": "MemTest86+"}, cfg["menu_alias"])
        self.assertIn({"image": imgs[0]["path"], "tip1": "a", "tip2": "b"}, cfg["menu_tip"]["tips"])


if __name__ == "__main__":
    unittest.main()
