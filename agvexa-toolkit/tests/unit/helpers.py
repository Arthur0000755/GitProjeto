"""Utilidades compartilhadas pelos testes unitários."""
import io
import os
import sys
import contextlib

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "scripts", "lib"))

import agvexa  # noqa: E402


def quiet_report():
    return agvexa.Report(quiet=True)


@contextlib.contextmanager
def silenced():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        yield buf


def make_fake_iso(path, size=40 * 1024, payload=b""):
    """Cria um arquivo pequeno com assinatura ISO 9660 (CD001 em 0x8001).
    Usado só em testes; o SHA-256 é calculado de verdade pelo teste."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = bytearray(max(size, 0x8800))
    data[0x8000] = 1
    data[0x8001:0x8006] = b"CD001"
    data[-len(payload) or len(data):] = payload
    with open(path, "wb") as fh:
        fh.write(bytes(data))
    return path
