"""Verificações estáticas do Windows Optimizer que rodam no Linux.

Não substituem a execução no Windows (ver docs/windows-optimizer.md,
'Plano de testes'), mas pegam erros comuns antes do laboratório:
codificação, cabeçalhos, balanceamento de blocos, sintaxe exclusiva do
PowerShell 7 e consistência do catálogo de ajustes."""
import json
import os
import re
import unittest

from tests.unit.helpers import ROOT

WO = os.path.join(ROOT, "windows-optimizer")
SCRIPTS = ["AGVexa-Optimizer.ps1", "Get-AGVexaSystemInfo.ps1", "Test-AGVexaOptimization.ps1",
           "Invoke-AGVexaOptimization.ps1", "Restore-AGVexaSettings.ps1", "New-AGVexaReport.ps1"]


# Aliases padrão do Windows PowerShell 5.1 (Get-Alias numa instalação limpa).
PS51_DEFAULT_ALIASES = set("""
% ? ac asnp cat cd chdir clc clear clhy cli clp cls clv cnsn compare copy cp cpi cpp curl cvpa
dbp del diff dir dnsn ebp echo epal epcsv epsn erase etsn exsn fc fhx fl foreach ft fw gal gbp
gc gcb gci gcm gcs gdr ghy gi gin gjb gl gm gmo gp gps gpv group gsn gsnp gsv gtz gu gv gwmi h
history icm iex ihy ii ipal ipcsv ipmo ipsn irm ise iwmi iwr kill lp ls man md measure mi mount
move mp mv nal ndr ni nmo npssc nsn nv ogv oh popd ps pushd pwd r rbp rcjb rcsn rd rdr ren ri
rjb rm rmdir rmo rni rnp rp rsn rsnp rujb rv rvpa rwmi sajb sal saps sasv sbp sc scb select set
shcm si sl sleep sls sort sp spjb spps spsv start stz sujb sv swmi tee trcm type wget where wjb
write
""".split())


def ps_files():
    for base in (WO, os.path.join(ROOT, "media-layout")):
        for p in _ps_files_in(base):
            yield p


def _ps_files_in(base):
    for dirpath, _d, files in os.walk(base):
        for f in files:
            if f.endswith((".ps1", ".psm1")):
                yield os.path.join(dirpath, f)


def strip_code(text):
    """Remove comentários, strings e here-strings, deixando só a estrutura."""
    out = []
    i, n = 0, len(text)
    while i < n:
        two = text[i:i + 2]
        if two in ("@'", '@"') and text[i + 2:i + 4].lstrip(" \t")[:1] in ("\n", "\r"):
            end = text.find("\n" + two[1] + "@", i + 2)
            if end < 0:
                raise ValueError("here-string sem fechamento")
            i = end + 3
            out.append("''")
            continue
        if two == "<#":
            end = text.find("#>", i + 2)
            if end < 0:
                raise ValueError("comentário de bloco sem fechamento")
            i = end + 2
            continue
        c = text[i]
        if c == "#":
            while i < n and text[i] != "\n":
                i += 1
            continue
        if c == "'":
            i += 1
            while i < n:
                if text[i] == "'" and text[i + 1:i + 2] == "'":
                    i += 2
                    continue
                if text[i] == "'":
                    break
                i += 1
            i += 1
            out.append("''")
            continue
        if c == '"':
            i += 1
            depth = 0
            while i < n:
                if text[i] == "`":
                    i += 2
                    continue
                if text[i:i + 2] == "$(":
                    depth += 1
                    i += 2
                    continue
                if text[i] == ")" and depth:
                    depth -= 1
                elif text[i] == '"' and not depth:
                    break
                i += 1
            i += 1
            out.append("''")
            continue
        out.append(c)
        i += 1
    return "".join(out)


class PowerShellStaticTests(unittest.TestCase):
    def test_all_required_scripts_exist(self):
        for s in SCRIPTS + ["lib/AGVexa.Common.psm1", "profiles/ajustes.json",
                            "tests/Invoke-AGVexaSelfTest.ps1", "tests/AGVexa.Optimizer.Tests.ps1", "LEIA-ME.md"]:
            self.assertTrue(os.path.isfile(os.path.join(WO, s)), s)

    def test_utf8_bom_when_non_ascii(self):
        # Windows PowerShell 5.1 lê .ps1 sem BOM como ANSI: acentos seriam corrompidos.
        for p in ps_files():
            raw = open(p, "rb").read()
            if any(b > 127 for b in raw):
                self.assertTrue(raw.startswith(b"\xef\xbb\xbf"), "%s precisa de UTF-8 com BOM" % p)
            raw.decode("utf-8-sig")

    def test_headers_and_help(self):
        for s in SCRIPTS:
            text = open(os.path.join(WO, s), encoding="utf-8-sig").read()
            self.assertTrue(text.startswith("#Requires -Version 5.1"), s)
            self.assertIn(".SYNOPSIS", text, s)
            self.assertIn("[CmdletBinding(", text, s)
            self.assertIn("Set-StrictMode -Version 2.0", text, s)

    def test_changing_scripts_support_whatif(self):
        for s in ("Invoke-AGVexaOptimization.ps1", "Restore-AGVexaSettings.ps1"):
            text = open(os.path.join(WO, s), encoding="utf-8-sig").read()
            self.assertIn("SupportsShouldProcess = $true", text, s)
            self.assertIn("$PSCmdlet.ShouldProcess", text, s)
            self.assertIn("Read-AGVexaConfirmation", text, s)

    def test_balanced_blocks(self):
        for p in ps_files():
            code = strip_code(open(p, encoding="utf-8-sig").read())
            for o, c in ("{}", "()", "[]"):
                self.assertEqual(code.count(o), code.count(c), "%s: '%s' x '%s'" % (os.path.basename(p), o, c))

    def test_no_powershell7_only_syntax(self):
        for p in ps_files():
            code = strip_code(open(p, encoding="utf-8-sig").read())
            for pat in (r"\?\?", r"\?\.", r"-AsHashtable", r"\s&&\s", r"\s\|\|\s", r"-Parallel\b",
                        r"\$IsWindows\b", r"-AdditionalChildPath"):
                self.assertIsNone(re.search(pat, code, re.M), "%s usa sintaxe/recurso do PS7: %s" % (p, pat))

    def test_function_names_do_not_shadow_builtin_aliases(self):
        # No PowerShell, alias tem precedência sobre função: "function H" vira Get-History (alias h).
        for p in ps_files():
            code = strip_code(open(p, encoding="utf-8-sig").read())
            for name in re.findall(r"(?im)^\s*function\s+([\w-]+)", code):
                self.assertNotIn(name.lower(), PS51_DEFAULT_ALIASES,
                                 "%s: função '%s' tem o nome de um alias padrão" % (os.path.basename(p), name))

    def test_no_psscriptroot_in_param_defaults(self):
        # $PSScriptRoot chega vazio nos valores padrão de param() com "powershell -File" (PS 5.1).
        for p in ps_files():
            code = strip_code(open(p, encoding="utf-8-sig").read())
            m = re.search(r"(?i)\bparam\s*\(", code)
            if not m:
                continue
            i, depth = m.end(), 1
            while depth and i < len(code):
                depth += {"(": 1, ")": -1}.get(code[i], 0)
                i += 1
            self.assertNotIn("$psscriptroot", code[m.start():i].lower(),
                             "%s: $PSScriptRoot no bloco param()" % os.path.basename(p))

    def test_no_include_with_literalpath(self):
        # Get-ChildItem -LiteralPath ignora -Include no PowerShell 5.1.
        for p in ps_files():
            code = strip_code(open(p, encoding="utf-8-sig").read())
            for line in code.splitlines():
                self.assertFalse("-LiteralPath" in line and re.search(r"-Include\b", line),
                                 "%s: -Include com -LiteralPath: %s" % (os.path.basename(p), line.strip()))

    def test_default_is_analysis_only(self):
        text = open(os.path.join(WO, "Invoke-AGVexaOptimization.ps1"), encoding="utf-8-sig").read()
        self.assertIn("[switch]$Aplicar", text)
        self.assertRegex(text, r"if \(-not \$Aplicar -or -not \$todo\.Count\) \{\s*if \(-not \$Aplicar\)")

    def test_twelve_steps_in_order(self):
        text = open(os.path.join(WO, "Invoke-AGVexaOptimization.ps1"), encoding="utf-8-sig").read()
        positions = []
        for n in range(1, 13):
            m = re.search(r"(?<!\d)%d/12 " % n, text)
            positions.append(m.start() if m else -1)
        self.assertTrue(all(p > 0 for p in positions), positions)
        self.assertEqual(positions, sorted(positions))

    def test_menu_has_all_options(self):
        text = open(os.path.join(WO, "AGVexa-Optimizer.ps1"), encoding="utf-8-sig").read()
        for opt in ("Diagnóstico do computador", "Otimização conservadora", "Otimização de desempenho",
                    "Personalizar ajustes", "Programas de inicialização", "Relatório técnico",
                    "Desfazer alterações", "Sair"):
            self.assertIn(opt, text)

    def test_version_matches_project(self):
        version = open(os.path.join(ROOT, "VERSION"), encoding="utf-8").read().strip()
        text = open(os.path.join(WO, "lib", "AGVexa.Common.psm1"), encoding="utf-8-sig").read()
        self.assertIn("$script:AGVVersion = '%s'" % version, text)

    def test_catalog(self):
        data = json.load(open(os.path.join(WO, "profiles", "ajustes.json"), encoding="utf-8"))
        self.assertEqual(data["schema"], "agvexa-optimizer-ajustes/1")
        ids = [a["id"] for a in data["ajustes"]]
        self.assertEqual(len(ids), len(set(ids)))
        types = {"recomendacao", "spi-animacao", "spi-bool", "registro", "plano-energia"}
        for a in data["ajustes"]:
            for k in ("id", "titulo", "tipo", "perfis", "requerAdmin", "o_que_muda", "beneficio", "riscos", "reversao"):
                self.assertIn(k, a, a["id"])
            self.assertIn(a["tipo"], types)
            self.assertTrue(set(a["perfis"]) <= {"Conservador", "Desempenho"}, a["id"])
            if a["tipo"] == "registro":
                self.assertTrue(a["chave"].startswith("HKCU:\\"), a["id"])
                self.assertIn("valorAlvo", a)
            if a["tipo"] == "spi-bool":
                self.assertEqual(a["spiSet"], a["spiGet"] + 1, a["id"])
            if a["tipo"] == "plano-energia":
                self.assertIn(a["condicao"], ("desktop", "notebook"))
                self.assertRegex(a["planoGuid"], r"^[0-9a-f-]{36}$")
        # Desempenho inclui todos os itens do Conservador
        cons = {a["id"] for a in data["ajustes"] if "Conservador" in a["perfis"]}
        perf = {a["id"] for a in data["ajustes"] if "Desempenho" in a["perfis"]}
        self.assertTrue(cons <= perf | {"energia.equilibrado-notebook"})

    def test_media_copy_checker(self):
        ps = os.path.join(ROOT, "media-layout", "AGVexa", "Verificar-Copia.ps1")
        cmd = os.path.join(ROOT, "media-layout", "VERIFICAR-COPIA.cmd")
        text = open(ps, encoding="utf-8-sig").read()
        self.assertTrue(text.startswith("#Requires -Version 5.1"))
        self.assertIn("SHA256SUMS-AGVEXA.txt", text)
        self.assertIn("Get-FileHash -Algorithm SHA256", text)
        for verb in ("Remove-Item", "Set-Content", "Out-File", "Move-Item", "Copy-Item", "New-Item"):
            self.assertNotIn(verb, text, "o verificador deve ser somente leitura")
        raw = open(cmd, "rb").read()
        self.assertIn(b"\r\n", raw)
        self.assertIn(b"AGVexa\\Verificar-Copia.ps1", raw)
        self.assertIn(b"-ExecutionPolicy Bypass", raw)

    def test_strip_code_helper(self):
        self.assertEqual(strip_code("a # {\n'{'\"$(x)}\"<# ( #>"), "a \n''''")


if __name__ == "__main__":
    unittest.main()
