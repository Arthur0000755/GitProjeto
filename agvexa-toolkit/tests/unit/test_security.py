"""Varredura estática de segurança: garante que nenhum script do projeto
contenha operações destrutivas, privilegiadas ou de rede fora do esperado.

Textos de ajuda (heredocs), comentários e documentação são ignorados: o
procedimento futuro de instalação é DOCUMENTADO, nunca executado."""
import json
import os
import re
import unittest

from tests.unit.helpers import ROOT

SHELL_FORBIDDEN = [
    r"\bsudo\b", r"\bmkfs(\.\w+)?\b", r"\bwipefs\b", r"\bparted\b", r"\bs?fdisk\b", r"\bgdisk\b",
    r"\blosetup\b", r"(^|\s)mount\s", r"\bumount\b", r"\bdd\b[^\n]*\bof=", r"Ventoy2Disk",
    r"/dev/(sd|nvme|hd|vd|mmcblk|loop)", r"\bsystemctl\b", r"\bdocker\b", r"\bnginx\b",
    r"\bapt(-get)?\s+install\b", r"\bpip3?\s+install\b", r"\bcurl\b", r"\bwget\b", r"\bshred\b",
    r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f?\s+/(\s|$)", r"\bchmod\s+-R\b", r"\bchown\b", r"\bblkdiscard\b",
]
PYTHON_FORBIDDEN = [
    r"\bsubprocess\b", r"\bos\.system\b", r"\bos\.popen\b", r"open\(\s*['\"]/dev/", r"\burllib\b",
    r"\brequests\b", r"\bsocket\b", r"\bhttp\.client\b", r"\bctypes\b",
]
PS_FORBIDDEN = [
    r"Set-MpPreference\b[^\n]*-Disable", r"Set-NetFirewallProfile\b[^\n]*-Enabled\s+(\$false|False|0)",
    r"netsh\s+advfirewall\s+set\b[^\n]*\boff\b", r"(Stop|Set)-Service\b[^\n]*(wuauserv|WinDefend|mpssvc|UsoSvc|BITS)",
    # escrita em chaves protegidas (leitura para diagnóstico é permitida)
    r"(Set-ItemProperty|New-ItemProperty|Remove-ItemProperty|Set-AGVexaRegistryValue|reg(\.exe)?\s+(add|delete))"
    r"[^\n]*(EnableLUA|Windows Defender|WindowsUpdate|\\FVE|Firewall|SystemRestore)",
    r"Disable-BitLocker", r"manage-bde\b[^\n]*-off", r"Suspend-BitLocker",
    r"Set-ExecutionPolicy(?![^\n]*-Scope\s+Process)", r"Invoke-Expression", r"\biex\b",
    r"DownloadString", r"DownloadFile", r"Invoke-WebRequest", r"Invoke-RestMethod", r"\biwr\b",
    r"Start-BitsTransfer", r"Disable-ComputerRestore", r"vssadmin[^\n]*delete", r"\bbcdedit\b",
    r"Remove-AppxPackage", r"Remove-AppxProvisionedPackage", r"Format-Volume", r"Clear-Disk",
    r"Initialize-Disk", r"Remove-Partition", r"\bdiskpart\b", r"Set-Partition", r"Remove-Item\b[^\n]*-Recurse",
    r"cipher\s+/w", r"Disable-WindowsOptionalFeature", r"Remove-WindowsCapability",
    r"PagingFiles",
    r"DisableDeleteNotify\s+(1|set)", r"Stop-Computer", r"Restart-Computer\b(?![^\n]*-WhatIf)",
]


def strip_shell(text):
    text = re.sub(r"<<-?'?(\w+)'?[^\n]*\n.*?\n\s*\1\n", "\n", text, flags=re.S)  # heredocs (ajuda/plano)
    return "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("#"))


def strip_python(text):
    text = re.sub(r'"""[\s\S]*?"""', "", text)
    return "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("#"))


def strip_ps(text):
    text = re.sub(r"<#[\s\S]*?#>", "", text)
    text = re.sub(r"@'[\s\S]*?'@|@\"[\s\S]*?\"@", "", text)
    return "\n".join(re.sub(r"(^|\s)#.*$", "", l) for l in text.splitlines())


def files(base, exts):
    for dirpath, _d, fs in os.walk(os.path.join(ROOT, base)):
        if "__pycache__" in dirpath:
            continue
        for f in fs:
            if f.endswith(exts):
                yield os.path.join(dirpath, f)


class SecurityScanTests(unittest.TestCase):
    def scan(self, paths, patterns, stripper, allow=None):
        found = []
        for p in paths:
            text = stripper(open(p, encoding="utf-8-sig").read())
            for pat in patterns:
                for m in re.finditer(pat, text, flags=re.M | re.I):
                    if allow and allow(p, pat, m):
                        continue
                    found.append("%s: %s" % (os.path.relpath(p, ROOT), m.group(0).strip()))
        return found

    def test_shell_scripts_have_no_destructive_commands(self):
        paths = list(files("scripts", (".sh",))) + list(files("tests", (".sh",)))
        self.assertEqual(self.scan(paths, SHELL_FORBIDDEN, strip_shell), [])

    def test_python_has_no_process_or_network_access(self):
        paths = [p for p in files("scripts", (".py",))]
        # test-boot.sh usa socket UNIX local só para o monitor do QEMU (inline, fora deste escopo)
        self.assertEqual(self.scan(paths, PYTHON_FORBIDDEN, strip_python), [])

    def test_powershell_has_no_forbidden_operations(self):
        paths = list(files("windows-optimizer", (".ps1", ".psm1")))
        self.assertTrue(paths, "nenhum script PowerShell encontrado")

        def allow(path, pat, m):
            # o autoteste remove apenas o diretório temporário com GUID que ele mesmo criou
            line = m.string[m.start():m.string.find("\n", m.start())]
            return path.endswith("Invoke-AGVexaSelfTest.ps1") and "Remove-Item" in pat and "$tmpRoot" in line

        self.assertEqual(self.scan(paths, PS_FORBIDDEN, strip_ps, allow), [])

    def test_optimizer_profiles_do_not_target_protected_settings(self):
        data = json.load(open(os.path.join(ROOT, "windows-optimizer", "profiles", "ajustes.json"), encoding="utf-8"))
        for a in data["ajustes"]:
            target = " ".join(str(a.get(k, "")) for k in ("chave", "valor", "planoGuid", "acao"))
            for pat in (r"Windows Defender", r"WindowsUpdate\\", r"EnableLUA", r"FVE", r"Firewall", r"PagingFiles",
                        r"SystemRestore", r"DisableAntiSpyware", r"Policies"):
                self.assertIsNone(re.search(pat, target, re.I), "%s: %s" % (a["id"], pat))

    def test_scanner_detects_known_bad_samples(self):
        # garante que a própria varredura funciona
        self.assertTrue(re.search(SHELL_FORBIDDEN[0], strip_shell("sudo rm x\n")))
        self.assertIsNone(re.search(SHELL_FORBIDDEN[0], strip_shell("cat <<EOF\nsudo x\nEOF\n")))
        self.assertTrue(any(re.search(p, strip_ps("Set-MpPreference -DisableRealtimeMonitoring $true"))
                            for p in PS_FORBIDDEN))
        self.assertFalse(any(re.search(p, strip_ps("# Set-MpPreference -DisableRealtimeMonitoring"))
                             for p in PS_FORBIDDEN))
        self.assertTrue(any(re.search(p, "Set-ItemProperty -Path $k -Name EnableLUA -Value 0") for p in PS_FORBIDDEN))
        self.assertFalse(any(re.search(p, "$v = Get-ItemProperty $k; $v.EnableLUA") for p in PS_FORBIDDEN))
        self.assertTrue(any(re.search(p, "Set-ExecutionPolicy Unrestricted") for p in PS_FORBIDDEN))
        self.assertFalse(any(re.search(p, "Set-ExecutionPolicy Bypass -Scope Process") for p in PS_FORBIDDEN))

    def test_no_large_or_proprietary_files_in_repo(self):
        big = []
        for dirpath, dirs, fs in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in (".git", "isos", "build", "reports", ".cache", "vendor")]
            for f in fs:
                p = os.path.join(dirpath, f)
                if f.lower().endswith((".iso", ".img", ".wim", ".esd", ".vhd", ".vhdx")):
                    big.append(p)
                elif os.path.getsize(p) > 2 * 1024 * 1024:
                    big.append(p)
        self.assertEqual(big, [])

    def test_gitignore_protects_isos_and_reports(self):
        text = open(os.path.join(ROOT, ".gitignore"), encoding="utf-8").read()
        for needed in ("*.iso", "isos/*", "build/*", "reports/*", "catalog/isos-manifest.json", ".env"):
            self.assertIn(needed, text)


if __name__ == "__main__":
    unittest.main()
