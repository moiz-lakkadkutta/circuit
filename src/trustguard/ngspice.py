"""
ngspice runner and availability helpers.
"""
import subprocess
import tempfile
from pathlib import Path

NGSPICE = "/opt/homebrew/bin/ngspice"


class NgspiceNotFound(Exception):
    """Raised when the ngspice binary cannot be found or executed."""


def ngspice_available(ngspice_path=None):
    """Return True iff the ngspice binary is runnable."""
    binary = ngspice_path or NGSPICE
    try:
        subprocess.run([binary, "--version"], capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return False


def run_ngspice_text(text, ngspice_path=None, cwd=None):
    """Run a netlist string through ngspice batch mode via a temp file.

    Returns (returncode, combined_log_text).
    """
    binary = ngspice_path or NGSPICE
    with tempfile.NamedTemporaryFile("w", suffix=".cir", delete=False) as f:
        f.write(text)
        tmp = f.name
    try:
        kwargs = dict(capture_output=True, text=True, timeout=120)
        if cwd is not None:
            kwargs["cwd"] = cwd
        p = subprocess.run([binary, "-b", tmp], **kwargs)
        return p.returncode, p.stdout + p.stderr
    finally:
        Path(tmp).unlink(missing_ok=True)
