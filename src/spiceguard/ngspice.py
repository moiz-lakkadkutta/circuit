"""
ngspice runner and availability helpers.
"""
import os
import shutil
import subprocess  # nosec B404 - used to invoke ngspice with a fixed argv (no shell)
import tempfile

NGSPICE = "/opt/homebrew/bin/ngspice"

# Wall-clock cap so a non-converging / hanging simulation can't block forever.
NGSPICE_TIMEOUT = 120


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

    Returns (returncode, combined_log_text). A timeout is reported as a
    non-zero return code with an explanatory log (never an exception to the
    caller). Raises NgspiceNotFound if no usable binary is available.

    Security: ngspice is invoked with ``--no-spiceinit`` so it does NOT
    auto-load a ``.spiceinit`` / ``spice.rc`` config from the working directory
    or home — otherwise a config file planted next to the netlist could execute
    arbitrary commands. (Note: a netlist's own ``.control``/``shell`` blocks can
    still run code — only check netlists you trust; see the README.)
    """
    binary = resolve_ngspice_path(explicit=ngspice_path)
    fd, tmp = tempfile.mkstemp(suffix=".cir")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
        kwargs = dict(capture_output=True, text=True, timeout=NGSPICE_TIMEOUT)
        if cwd is not None:
            kwargs["cwd"] = cwd
        try:
            # Fixed argv, shell=False; `binary` is a user-chosen simulator path,
            # `tmp` is our own temp file. -n / --no-spiceinit disables config
            # auto-loading.
            p = subprocess.run([binary, "-b", "-n", tmp], **kwargs)  # nosec B603
        except subprocess.TimeoutExpired:
            return 124, (
                f"ngspice timed out after {NGSPICE_TIMEOUT}s and was terminated. "
                f"The simulation is likely hanging (e.g. a non-converging "
                f"transient). Treat this result as FAILED."
            )
        return p.returncode, p.stdout + p.stderr
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass
