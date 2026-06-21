"""
Unit tests for resolve_ngspice_path (AC-A1, AC-A2).
Pure: no real ngspice needed. All filesystem / env effects are monkeypatched.
"""
import os
import shutil
import types

import pytest

from spiceguard.ngspice import NgspiceNotFound, resolve_ngspice_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAKE_BIN = "/fake/bin/ngspice"
FAKE_ENV = "/env/bin/ngspice"
FAKE_WHICH = "/usr/local/bin/ngspice"
LEGACY = "/opt/homebrew/bin/ngspice"


def _make_access(executable_paths):
    """Return an os.access replacement that reports X_OK only for given paths."""
    def _access(path, mode):
        if mode == os.X_OK:
            return path in executable_paths
        return True
    return _access


# ---------------------------------------------------------------------------
# AC-A1: priority tier 1 — explicit arg wins when usable
# ---------------------------------------------------------------------------

class TestExplicitArg:
    def test_explicit_usable_returned(self, monkeypatch):
        monkeypatch.delenv("NGSPICE", raising=False)
        monkeypatch.setattr(shutil, "which", lambda _: FAKE_WHICH)
        monkeypatch.setattr(os, "access", _make_access({FAKE_BIN}))

        result = resolve_ngspice_path(explicit=FAKE_BIN)
        assert result == FAKE_BIN

    def test_explicit_not_executable_raises(self, monkeypatch):
        monkeypatch.delenv("NGSPICE", raising=False)
        monkeypatch.setattr(shutil, "which", lambda _: FAKE_WHICH)
        # FAKE_BIN is NOT executable — access returns False for it
        monkeypatch.setattr(os, "access", _make_access({FAKE_WHICH}))

        with pytest.raises(NgspiceNotFound) as exc_info:
            resolve_ngspice_path(explicit=FAKE_BIN)
        assert FAKE_BIN in str(exc_info.value)

    def test_explicit_not_usable_does_not_fall_through_to_which(self, monkeypatch):
        """When explicit is given but broken, we raise — not silently fall back."""
        monkeypatch.delenv("NGSPICE", raising=False)
        monkeypatch.setattr(shutil, "which", lambda _: FAKE_WHICH)
        monkeypatch.setattr(os, "access", _make_access({FAKE_WHICH}))

        with pytest.raises(NgspiceNotFound):
            resolve_ngspice_path(explicit=FAKE_BIN)

    def test_explicit_wins_over_env_and_which(self, monkeypatch):
        """explicit beats $NGSPICE and which()."""
        monkeypatch.setenv("NGSPICE", FAKE_ENV)
        monkeypatch.setattr(shutil, "which", lambda _: FAKE_WHICH)
        monkeypatch.setattr(os, "access", _make_access({FAKE_BIN, FAKE_ENV, FAKE_WHICH}))

        result = resolve_ngspice_path(explicit=FAKE_BIN)
        assert result == FAKE_BIN


# ---------------------------------------------------------------------------
# AC-A1: priority tier 2 — $NGSPICE env var
# ---------------------------------------------------------------------------

class TestEnvVar:
    def test_env_usable_returned(self, monkeypatch):
        monkeypatch.setenv("NGSPICE", FAKE_ENV)
        monkeypatch.setattr(shutil, "which", lambda _: FAKE_WHICH)
        monkeypatch.setattr(os, "access", _make_access({FAKE_ENV}))

        result = resolve_ngspice_path(explicit=None)
        assert result == FAKE_ENV

    def test_env_not_executable_raises(self, monkeypatch):
        monkeypatch.setenv("NGSPICE", FAKE_ENV)
        monkeypatch.setattr(shutil, "which", lambda _: FAKE_WHICH)
        monkeypatch.setattr(os, "access", _make_access({FAKE_WHICH}))  # env not executable

        with pytest.raises(NgspiceNotFound) as exc_info:
            resolve_ngspice_path(explicit=None)
        assert FAKE_ENV in str(exc_info.value)

    def test_env_broken_does_not_fall_through_to_which(self, monkeypatch):
        """When $NGSPICE is set but broken, raise — don't fall back to which()."""
        monkeypatch.setenv("NGSPICE", FAKE_ENV)
        monkeypatch.setattr(shutil, "which", lambda _: FAKE_WHICH)
        monkeypatch.setattr(os, "access", _make_access({FAKE_WHICH}))

        with pytest.raises(NgspiceNotFound):
            resolve_ngspice_path(explicit=None)

    def test_env_wins_over_which(self, monkeypatch):
        monkeypatch.setenv("NGSPICE", FAKE_ENV)
        monkeypatch.setattr(shutil, "which", lambda _: FAKE_WHICH)
        monkeypatch.setattr(os, "access", _make_access({FAKE_ENV, FAKE_WHICH}))

        result = resolve_ngspice_path(explicit=None)
        assert result == FAKE_ENV


# ---------------------------------------------------------------------------
# AC-A1: priority tier 3 — shutil.which("ngspice")
# ---------------------------------------------------------------------------

class TestWhich:
    def test_which_used_when_explicit_and_env_absent(self, monkeypatch):
        monkeypatch.delenv("NGSPICE", raising=False)
        monkeypatch.setattr(shutil, "which", lambda _: FAKE_WHICH)
        # os.access not needed for which() tier (which implies executable)
        monkeypatch.setattr(os, "access", _make_access({}))

        result = resolve_ngspice_path(explicit=None)
        assert result == FAKE_WHICH

    def test_which_none_falls_to_legacy(self, monkeypatch):
        monkeypatch.delenv("NGSPICE", raising=False)
        monkeypatch.setattr(shutil, "which", lambda _: None)
        monkeypatch.setattr(os, "access", _make_access({LEGACY}))

        result = resolve_ngspice_path(explicit=None)
        assert result == LEGACY


# ---------------------------------------------------------------------------
# AC-A1: priority tier 4 — legacy fallback
# ---------------------------------------------------------------------------

class TestLegacyFallback:
    def test_legacy_returned_when_only_usable(self, monkeypatch):
        monkeypatch.delenv("NGSPICE", raising=False)
        monkeypatch.setattr(shutil, "which", lambda _: None)
        monkeypatch.setattr(os, "access", _make_access({LEGACY}))

        result = resolve_ngspice_path(explicit=None)
        assert result == LEGACY

    def test_legacy_not_usable_and_no_other_raises(self, monkeypatch):
        monkeypatch.delenv("NGSPICE", raising=False)
        monkeypatch.setattr(shutil, "which", lambda _: None)
        monkeypatch.setattr(os, "access", _make_access({}))  # nothing executable

        with pytest.raises(NgspiceNotFound):
            resolve_ngspice_path(explicit=None)


# ---------------------------------------------------------------------------
# AC-A2: NgspiceNotFound message must name what was tried
# ---------------------------------------------------------------------------

class TestNotFoundMessage:
    def test_message_names_tried_candidates_all_missing(self, monkeypatch):
        monkeypatch.delenv("NGSPICE", raising=False)
        monkeypatch.setattr(shutil, "which", lambda _: None)
        monkeypatch.setattr(os, "access", _make_access({}))

        with pytest.raises(NgspiceNotFound) as exc_info:
            resolve_ngspice_path(explicit=None)
        msg = str(exc_info.value)
        # The message should mention the legacy path that was tried
        assert LEGACY in msg or "ngspice" in msg.lower()

    def test_message_names_explicit_path_when_broken(self, monkeypatch):
        monkeypatch.delenv("NGSPICE", raising=False)
        monkeypatch.setattr(shutil, "which", lambda _: None)
        monkeypatch.setattr(os, "access", _make_access({}))

        with pytest.raises(NgspiceNotFound) as exc_info:
            resolve_ngspice_path(explicit=FAKE_BIN)
        assert FAKE_BIN in str(exc_info.value)

    def test_message_names_env_path_when_broken(self, monkeypatch):
        monkeypatch.setenv("NGSPICE", FAKE_ENV)
        monkeypatch.setattr(shutil, "which", lambda _: None)
        monkeypatch.setattr(os, "access", _make_access({}))

        with pytest.raises(NgspiceNotFound) as exc_info:
            resolve_ngspice_path(explicit=None)
        assert FAKE_ENV in str(exc_info.value)


# ---------------------------------------------------------------------------
# run_ngspice_text wires through resolve_ngspice_path
# ---------------------------------------------------------------------------

class TestRunNgspiceTextWiring:
    def test_raises_ngspice_not_found_when_binary_missing(self, monkeypatch):
        """run_ngspice_text should raise NgspiceNotFound (not FileNotFoundError)."""
        monkeypatch.delenv("NGSPICE", raising=False)
        monkeypatch.setattr(shutil, "which", lambda _: None)
        monkeypatch.setattr(os, "access", _make_access({}))

        from spiceguard.ngspice import run_ngspice_text
        with pytest.raises(NgspiceNotFound):
            run_ngspice_text("* test netlist\n.end\n")

    def test_explicit_ngspice_path_forwarded_to_subprocess_argv0(self, monkeypatch):
        """run_ngspice_text(ngspice_path=X) must use X as subprocess argv[0]."""
        import spiceguard.ngspice as _mod

        CUSTOM = "/custom/ng"
        captured = {}

        # Patch resolve so /custom/ng is accepted without real filesystem access
        def fake_resolve(explicit=None):
            captured["resolve_explicit"] = explicit
            return CUSTOM

        def fake_subprocess_run(cmd, **kwargs):
            captured["cmd"] = list(cmd)
            captured["kwargs"] = dict(kwargs)
            return types.SimpleNamespace(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(_mod, "resolve_ngspice_path", fake_resolve)
        monkeypatch.setattr(_mod.subprocess, "run", fake_subprocess_run)

        _mod.run_ngspice_text("* test\n.end\n", ngspice_path=CUSTOM, cwd="/some/dir")

        # resolve was called with the explicit path
        assert captured["resolve_explicit"] == CUSTOM
        # binary forwarded as argv[0]
        assert captured["cmd"][0] == CUSTOM
        # cwd forwarded to subprocess.run
        assert captured["kwargs"].get("cwd") == "/some/dir"

    def test_no_explicit_path_uses_resolver_choice_as_argv0(self, monkeypatch):
        """run_ngspice_text() with no path uses whatever resolve_ngspice_path returns."""
        import spiceguard.ngspice as _mod

        RESOLVED = "/resolved/ngspice"
        captured = {}

        def fake_resolve(explicit=None):
            captured["resolve_explicit"] = explicit
            return RESOLVED

        def fake_subprocess_run(cmd, **kwargs):
            captured["cmd"] = list(cmd)
            captured["kwargs"] = dict(kwargs)
            return types.SimpleNamespace(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(_mod, "resolve_ngspice_path", fake_resolve)
        monkeypatch.setattr(_mod.subprocess, "run", fake_subprocess_run)

        _mod.run_ngspice_text("* test\n.end\n")

        # resolve called with explicit=None (no path supplied)
        assert captured["resolve_explicit"] is None
        # binary is the resolved choice
        assert captured["cmd"][0] == RESOLVED
        # cwd not forwarded when not supplied
        assert "cwd" not in captured["kwargs"]


# ---------------------------------------------------------------------------
# ngspice_available reflects resolve_ngspice_path
# ---------------------------------------------------------------------------

class TestNgspiceAvailable:
    def test_returns_true_when_resolvable(self, monkeypatch):
        monkeypatch.delenv("NGSPICE", raising=False)
        monkeypatch.setattr(shutil, "which", lambda _: FAKE_WHICH)
        monkeypatch.setattr(os, "access", _make_access({}))

        from spiceguard.ngspice import ngspice_available
        assert ngspice_available() is True

    def test_returns_false_when_nothing_found(self, monkeypatch):
        monkeypatch.delenv("NGSPICE", raising=False)
        monkeypatch.setattr(shutil, "which", lambda _: None)
        monkeypatch.setattr(os, "access", _make_access({}))

        from spiceguard.ngspice import ngspice_available
        assert ngspice_available() is False

    def test_returns_true_when_resolve_succeeds_via_direct_patch(self, monkeypatch):
        """ngspice_available must route through resolve_ngspice_path (direct monkeypatch)."""
        import spiceguard.ngspice as _mod

        monkeypatch.setattr(_mod, "resolve_ngspice_path", lambda explicit=None: "/patched/ng")

        assert _mod.ngspice_available() is True

    def test_returns_false_when_resolve_raises_via_direct_patch(self, monkeypatch):
        """ngspice_available must return False when resolve_ngspice_path raises NgspiceNotFound."""
        import spiceguard.ngspice as _mod

        def fake_resolve(explicit=None):
            raise NgspiceNotFound("patched not found")

        monkeypatch.setattr(_mod, "resolve_ngspice_path", fake_resolve)

        assert _mod.ngspice_available() is False
