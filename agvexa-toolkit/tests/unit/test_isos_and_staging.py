"""Testes da verificação de ISOs e da preparação do staging.

Usa imagens minúsculas criadas no próprio teste (assinatura ISO 9660 falsa,
conteúdo trivial). Os SHA-256 'oficiais' do teste são calculados aqui
mesmo, apenas para simular a comparação; o projeto nunca faz isso com ISOs reais.
"""
import argparse
import hashlib
import json
import os
import shutil
import tempfile
import unittest

from tests.unit.helpers import ROOT, agvexa, make_fake_iso, quiet_report, silenced


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


class IsoVerificationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="agv-iso-")
        self.lib = os.path.join(self.tmp, "isos")
        os.makedirs(self.lib)
        self.items = []

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def item(self, iid, arquivo, **kw):
        base = {"id": iid, "nome": iid, "categoria": "02-diagnostico-hardware", "arquivo": arquivo,
                "alias_menu": iid, "fonte_oficial": "https://exemplo.invalid/", "licenca": "GPL",
                "redistribuicao": "permitida", "habilitado": True, "sha256": None}
        base.update(kw)
        self.items.append(base)

    def run_verify(self):
        man = os.path.join(self.tmp, "manifest.json")
        with open(man, "w", encoding="utf-8") as fh:
            json.dump({"schema": "agvexa-isos-manifest/1", "itens": self.items}, fh)
        return {r["id"] or r["arquivo"]: r for r in agvexa.verify_isos(man, self.lib, use_cache=False, quiet=True)}

    def test_statuses(self):
        good = make_fake_iso(os.path.join(self.lib, "a/good.iso"), payload=b"good")
        bad = make_fake_iso(os.path.join(self.lib, "a/bad.iso"), payload=b"bad")
        make_fake_iso(os.path.join(self.lib, "a/nosum.iso"), payload=b"nosum")
        with open(os.path.join(self.lib, "a/notiso.iso"), "wb") as fh:
            fh.write(b"\x00" * 50000)
        sized = make_fake_iso(os.path.join(self.lib, "a/sized.iso"))
        make_fake_iso(os.path.join(self.lib, "a/extra.iso"), payload=b"extra")
        self.item("good", "a/good.iso", sha256=sha(good))
        self.item("bad", "a/bad.iso", sha256="0" * 64)
        self.item("nosum", "a/nosum.iso")
        self.item("notiso", "a/notiso.iso")
        self.item("missing", "a/missing.iso")
        self.item("sized", "a/sized.iso", tamanho_bytes=os.path.getsize(sized) + 1)
        self.item("off", "a/off.iso", habilitado=False)
        res = self.run_verify()
        self.assertEqual(res["good"]["status"], agvexa.ISO_STATUS_OK)
        self.assertEqual(res["bad"]["status"], agvexa.ISO_STATUS_MISMATCH)
        self.assertEqual(res["nosum"]["status"], agvexa.ISO_STATUS_UNVERIFIED)
        self.assertEqual(res["notiso"]["status"], agvexa.ISO_STATUS_BADTYPE)
        self.assertEqual(res["missing"]["status"], agvexa.ISO_STATUS_MISSING)
        self.assertEqual(res["sized"]["status"], agvexa.ISO_STATUS_BADSIZE)
        self.assertEqual(res["off"]["status"], agvexa.ISO_STATUS_DISABLED)
        self.assertEqual(res[os.path.join("a", "extra.iso")]["status"], agvexa.ISO_STATUS_UNCATALOGED)

    def test_official_checksums_file_gnu_and_bsd(self):
        f1 = make_fake_iso(os.path.join(self.lib, "u/one.iso"), payload=b"1")
        f2 = make_fake_iso(os.path.join(self.lib, "u/two.iso"), payload=b"2")
        with open(os.path.join(self.lib, "u/SHA256SUMS"), "w") as fh:
            fh.write("%s *one.iso\nSHA256 (two.iso) = %s\n" % (sha(f1), sha(f2)))
        self.item("one", "u/one.iso", arquivo_checksums="u/SHA256SUMS")
        self.item("two", "u/two.iso", arquivo_checksums="u/SHA256SUMS")
        res = self.run_verify()
        self.assertEqual(res["one"]["status"], agvexa.ISO_STATUS_OK)
        self.assertEqual(res["two"]["status"], agvexa.ISO_STATUS_OK)

    def test_disk_image_detection(self):
        p = os.path.join(self.lib, "d.img")
        data = bytearray(4096)
        data[510:512] = b"\x55\xaa"
        open(p, "wb").write(bytes(data))
        self.assertEqual(agvexa.detect_type(p), "disco-mbr")
        data[512:520] = b"EFI PART"
        open(p, "wb").write(bytes(data))
        self.assertEqual(agvexa.detect_type(p), "disco-gpt")

    def test_sha_cache_reused(self):
        p = make_fake_iso(os.path.join(self.lib, "c.iso"))
        cache = {}
        d1, hit1 = agvexa.sha256_file(p, cache)
        d2, hit2 = agvexa.sha256_file(p, cache)
        self.assertEqual(d1, d2)
        self.assertFalse(hit1)
        self.assertTrue(hit2)

    def test_example_manifest_valid(self):
        r = quiet_report()
        agvexa.validate_manifest(os.path.join(ROOT, "catalog", "isos-manifest.example.json"), r,
                                 agvexa.load_categories())
        self.assertEqual(r.errors, [])

    def test_example_manifest_has_no_fake_checksums(self):
        data, _ = agvexa.load_json(os.path.join(ROOT, "catalog", "isos-manifest.example.json"))
        self.assertTrue(all(i["sha256"] is None for i in data["itens"]))

    def test_manifest_rejects_unsafe_path(self):
        p = os.path.join(self.tmp, "m.json")
        with open(p, "w") as fh:
            json.dump({"schema": "agvexa-isos-manifest/1", "itens": [{
                "id": "x", "nome": "x", "categoria": "02-diagnostico-hardware", "arquivo": "../../etc/x.iso",
                "alias_menu": "x", "fonte_oficial": "http://inseguro", "licenca": "x",
                "redistribuicao": "x", "habilitado": True, "sha256": "zz"}]}, fh)
        r = quiet_report()
        agvexa.validate_manifest(p, r, agvexa.load_categories())
        self.assertGreaterEqual(len(r.errors), 3)


class StagingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="agv-stg-")
        self.lib = os.path.join(self.tmp, "isos")
        self.out = os.path.join(agvexa.STAGING_BASE, "teste-unitario-%d" % os.getpid())
        good = make_fake_iso(os.path.join(self.lib, "mt/mt.iso"), payload=b"mt")
        make_fake_iso(os.path.join(self.lib, "sr/sr.iso"), payload=b"sr")
        bad = make_fake_iso(os.path.join(self.lib, "gp/gp.iso"), payload=b"gp")
        items = [
            {"id": "mt", "nome": "MemTest", "categoria": "02-diagnostico-hardware", "arquivo": "mt/mt.iso",
             "alias_menu": "MemTest86+ — Teste", "dica1": "d1", "dica2": "d2", "sha256": sha(good)},
            {"id": "sr", "nome": "SR", "categoria": "05-linux-live", "arquivo": "sr/sr.iso",
             "alias_menu": "SystemRescue", "sha256": None},
            {"id": "gp", "nome": "GP", "categoria": "03-manutencao-discos", "arquivo": "gp/gp.iso",
             "alias_menu": "GParted", "sha256": "f" * 64},
        ]
        for i in items:
            i.update({"fonte_oficial": "https://x.invalid/", "licenca": "GPL", "redistribuicao": "permitida",
                      "habilitado": True})
        self.man = os.path.join(self.tmp, "manifest.json")
        with open(self.man, "w", encoding="utf-8") as fh:
            json.dump({"schema": "agvexa-isos-manifest/1", "itens": items}, fh, ensure_ascii=False)
        self.bad_hash = sha(bad)
        self.extras = os.path.join(self.tmp, "extras")
        os.makedirs(os.path.join(self.extras, "DRIVERS", "Lenovo"))
        with open(os.path.join(self.extras, "DRIVERS", "Lenovo", "wifi_1.0.exe"), "wb") as fh:
            fh.write(b"driver de teste")
        with open(os.path.join(self.extras, "DRIVERS", "INVENTARIO.csv"), "w", encoding="utf-8") as fh:
            fh.write("arquivo;origem\nwifi_1.0.exe;https://pcsupport.lenovo.com\n")

    def tearDown(self):
        shutil.rmtree(self.tmp)
        if os.path.isdir(self.out):
            shutil.rmtree(self.out)

    def stage(self, **kw):
        args = argparse.Namespace(output=self.out, manifest=self.man, library=self.lib, extras=self.extras,
                                  iso_mode="copy",
                                  allow_unverified=False, ascii_menu=False, dry_run=False, verbose=False)
        for k, v in kw.items():
            setattr(args, k, v)
        with silenced():
            return agvexa.cmd_stage(args)

    def cfg(self):
        return agvexa.load_json(os.path.join(self.out, "ventoy", "ventoy.json"))[0]

    def test_only_verified_isos_are_staged(self):
        self.assertEqual(self.stage(), 0)
        self.assertTrue(os.path.isfile(os.path.join(self.out, "ISO/02-diagnostico-hardware/mt.iso")))
        self.assertFalse(os.path.exists(os.path.join(self.out, "ISO/05-linux-live/sr.iso")))
        self.assertFalse(os.path.exists(os.path.join(self.out, "ISO/03-manutencao-discos/gp.iso")))
        aliases = {a.get("image"): a["alias"] for a in self.cfg()["menu_alias"]}
        self.assertEqual(aliases["/ISO/02-diagnostico-hardware/mt.iso"], "MemTest86+ — Teste")
        self.assertNotIn("/ISO/03-manutencao-discos/gp.iso", aliases)

    def test_allow_unverified_marks_menu(self):
        self.assertEqual(self.stage(allow_unverified=True), 0)
        aliases = {a.get("image"): a["alias"] for a in self.cfg()["menu_alias"]}
        self.assertIn("[NÃO VERIFICADA]", aliases["/ISO/05-linux-live/sr.iso"])
        # divergente nunca entra, nem com --allow-unverified
        self.assertNotIn("/ISO/03-manutencao-discos/gp.iso", aliases)

    def test_layout_and_validation(self):
        self.assertEqual(self.stage(), 0)
        for p in ("ventoy/ventoy.json", "ventoy/ventoy_grub.cfg", "ventoy/themes/agvexa/theme.txt",
                  "ventoy/themes/agvexa-lite/theme.txt", "AGVexa/.ventoyignore", "AGVexa/docs/manual-do-tecnico.md",
                  "AGVexa/windows-optimizer/AGVexa-Optimizer.ps1", "AGVexa/VERSION", "LEIA-ME.txt",
                  "SHA256SUMS-AGVEXA.txt", ".agvexa-staging"):
            self.assertTrue(os.path.exists(os.path.join(self.out, p)), p)
        for c in agvexa.load_categories()["categorias"]:
            self.assertTrue(os.path.isdir(os.path.join(self.out, "ISO", c["id"])))
        r = quiet_report()
        agvexa.validate_staging(self.out, r)
        self.assertEqual(r.errors, [])

    def test_checksums_cover_isos(self):
        self.stage()
        text = open(os.path.join(self.out, "SHA256SUMS-AGVEXA.txt"), encoding="utf-8").read()
        self.assertIn("ISO/02-diagnostico-hardware/mt.iso", text)
        for line in text.splitlines():
            digest, name = line.split("  ", 1)
            self.assertEqual(digest, sha(os.path.join(self.out, name)), name)

    def test_link_mode_uses_symlinks(self):
        self.assertEqual(self.stage(iso_mode="link"), 0)
        self.assertTrue(os.path.islink(os.path.join(self.out, "ISO/02-diagnostico-hardware/mt.iso")))

    def test_none_mode_without_manifest(self):
        self.assertEqual(self.stage(iso_mode="none", manifest="/nao/existe.json"), 0)
        self.assertFalse([a for a in self.cfg()["menu_alias"] if "image" in a])

    def test_dry_run_writes_nothing(self):
        self.assertEqual(self.stage(dry_run=True), 0)
        self.assertFalse(os.path.exists(self.out))

    def test_restage_replaces_previous(self):
        self.stage()
        marker = os.path.join(self.out, "ISO", "sobra.txt")
        open(marker, "w").write("x")
        self.stage()
        self.assertFalse(os.path.exists(marker))

    def test_refuses_output_outside_build(self):
        for bad in ("/tmp/agv-fora", "/dev/sdz", ROOT, agvexa.STAGING_BASE):
            with self.assertRaises(ValueError):
                agvexa.safe_staging_dir(bad)

    def test_refuses_unmarked_nonempty_dir(self):
        os.makedirs(self.out)
        keep = os.path.join(self.out, "importante.txt")
        open(keep, "w").write("não apagar")
        self.assertEqual(self.stage(), agvexa.EXIT_USAGE)
        self.assertTrue(os.path.isfile(keep))

    def test_refuses_symlink_output(self):
        target = tempfile.mkdtemp(prefix="agv-alvo-")
        try:
            os.symlink(target, self.out)
            with self.assertRaises(ValueError):
                agvexa.safe_staging_dir(self.out)
        finally:
            if os.path.islink(self.out):
                os.unlink(self.out)
            shutil.rmtree(target)

    def test_support_folders_present(self):
        self.assertEqual(self.stage(iso_mode="none"), 0)
        for folder in agvexa.EXTRA_FOLDERS:
            for f in ("LEIA-ME.txt", "INVENTARIO.csv", ".ventoyignore"):
                self.assertTrue(os.path.isfile(os.path.join(self.out, folder, f)), (folder, f))
        self.assertFalse(os.path.exists(os.path.join(self.out, "DRIVERS", "Lenovo")))  # none = sem arquivos

    def test_extras_copied_and_inventory_replaced(self):
        self.assertEqual(self.stage(), 0)
        drv = os.path.join(self.out, "DRIVERS", "Lenovo", "wifi_1.0.exe")
        self.assertTrue(os.path.isfile(drv) and not os.path.islink(drv))
        inv = open(os.path.join(self.out, "DRIVERS", "INVENTARIO.csv"), encoding="utf-8").read()
        self.assertIn("lenovo.com", inv)
        sums = open(os.path.join(self.out, "SHA256SUMS-AGVEXA.txt"), encoding="utf-8").read()
        self.assertIn("DRIVERS/Lenovo/wifi_1.0.exe", sums)
        r = quiet_report()
        agvexa.validate_staging(self.out, r)
        self.assertEqual(r.errors, [])

    def test_extras_linked_in_link_mode(self):
        self.assertEqual(self.stage(iso_mode="link"), 0)
        self.assertTrue(os.path.islink(os.path.join(self.out, "DRIVERS", "Lenovo", "wifi_1.0.exe")))

    def test_clientes_folder_refused_before_writing(self):
        os.makedirs(os.path.join(self.extras, "Clientes", "OS-123"))
        open(os.path.join(self.extras, "Clientes", "OS-123", "dados.txt"), "w").write("x")
        self.assertEqual(self.stage(), agvexa.EXIT_ERROR)
        self.assertFalse(os.path.exists(self.out))

    def test_unknown_extras_folder_ignored(self):
        os.makedirs(os.path.join(self.extras, "Musicas"))
        open(os.path.join(self.extras, "Musicas", "a.mp3"), "w").write("x")
        self.assertEqual(self.stage(), 0)
        self.assertFalse(os.path.exists(os.path.join(self.out, "Musicas")))

    def test_validate_staging_rejects_clientes(self):
        self.stage()
        os.makedirs(os.path.join(self.out, "CLIENTES"))
        r = quiet_report()
        agvexa.validate_staging(self.out, r)
        self.assertTrue(any("CLIENTES" in e for e in r.errors))

    def test_ascii_menu_staging(self):
        self.stage(ascii_menu=True)
        for a in self.cfg()["menu_alias"]:
            self.assertTrue(a["alias"].isascii(), a["alias"])


if __name__ == "__main__":
    unittest.main()
