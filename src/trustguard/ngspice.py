"""
ngspice runner and availability helpers.
"""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

NGSPICE = "/opt/homebrew/bin/ngspice"


class NgspiceNotFound(Exception):
    """Raised when the ngspice binary cannot be found or executed."""


def resolve_ngspice_path(explicit=None) -> str:
    """Return the first usable ngspice binary path, in priority order:

    1. *explicit* argument (the --ngspice CLI flag) if given
    2. $NGSPICE environment variable if set
    3. shutil.which("ngspice")
    4. Legacy fallback /opt/homebrew/bin/ngspice

    "Usable" = path exists and is executable (os.access X_OK).
    For which(), executability is already implied.

    Tiers 1 and 2 are "hard-configured": if the path is given but not usable
    we raise NgspiceNotFound immediately (no silent fall-through).
    Tiers 3 and 4 are "try-next-on-miss".

    Raises NgspiceNotFound if no usable binary can be found.
    """
    tried = []

    # Tier 1: explicit argument
    if explicit is not None:
        if os.access(explicit, os.X_OK):
            return explicit
        raise NgspiceNotFound(
            f"ngspice binary specified explicitly as '{explicit}' "
            f"is not executable or does not exist."
        )

    # Tier 2: $NGSPICE environment variable
    env_path = os.environ.get("NGSPICE")
    if env_path:
        if os.access(env_path, os.X_OK):
            return env_path
        raise NgspiceNotFound(
            f"$NGSPICE is set to '{env_path}' "
            f"but that path is not executable or does not exist."
        )
    tried.append("$NGSPICE (not set)")

    # Tier 3: shutil.which("ngspice")
    which_path = shutil.which("ngspice")
    if which_path is not None:
        return which_path
    tried.append("which('ngspice') -> not found")

    # Tier 4: legacy fallback
    if os.access(NGSPICE, os.X_OK):
        return NGSPICE
    tried.append(f"legacy fallback '{NGSPICE}' -> not executable")

    raise NgspiceNotFound(
        f"ngspice binary not found. Tried: {'; '.join(tried)}. "
        f"Install ngspice or set $NGSPICE / use --ngspice <path>."
    )


def ngspice_available(ngspice_path=None):
    """Return True iff a usable ngspice binary can be resolved."""
    try:
        resolve_ngspice_path(explicit=ngspice_path)
        return True
    except NgspiceNotFound:
        return False


def run_ngspice_text(text, ngspice_path=None, cwd=None):
    """Run a netlist string through ngspice batch mode via a temp file.

    Returns (returncode, combined_log_text).
    Raises NgspiceNotFound if no usable binary is available.
    """
    binary = resolve_ngspice_path(explicit=ngspice_path)
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
