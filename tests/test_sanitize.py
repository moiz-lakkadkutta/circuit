"""Tests for the no-exec netlist sanitizer (security gate for MCP/CI paths)."""
from spiceguard.sanitize import sanitize_netlist


def test_strips_control_block():
    text = (
        "v1 1 0 5\n"
        ".control\n"
        "shell rm -rf /\n"
        "run\n"
        ".endc\n"
        "r1 1 0 1k\n"
        ".end\n"
    )
    res = sanitize_netlist(text)
    assert ".control" not in res.text.lower()
    assert "shell" not in res.text.lower()
    assert "v1 1 0 5" in res.text
    assert "r1 1 0 1k" in res.text
    assert res.removed_blocks == 1


def test_strips_control_case_insensitive_and_multiple():
    text = ".CONTROL\nrun\n.ENDC\nv1 1 0 1\n.Control\nprint all\n.EndC\n.end\n"
    res = sanitize_netlist(text)
    assert res.removed_blocks == 2
    assert "run" not in res.text
    assert "print all" not in res.text


def test_unterminated_control_block_strips_to_eof():
    text = "v1 1 0 5\n.control\nshell echo pwned\n"  # no .endc
    res = sanitize_netlist(text)
    assert "shell" not in res.text
    assert res.removed_blocks == 1


def test_strips_include_and_inc_lines():
    text = "v1 1 0 5\n.include /etc/passwd\n.INC secrets.lib\nr1 1 0 1k\n.end\n"
    res = sanitize_netlist(text)
    assert ".include" not in res.text.lower()
    assert ".inc" not in res.text.lower()
    assert res.removed_includes == [".include /etc/passwd", ".INC secrets.lib"]


def test_does_not_strip_element_lines_containing_inc_substring():
    # 'rinc' is an element name, not a directive; '.ic' is a legit directive.
    text = "rinc 1 0 1k\n.ic v(1)=0\n.end\n"
    res = sanitize_netlist(text)
    assert "rinc 1 0 1k" in res.text
    assert ".ic v(1)=0" in res.text
    assert res.removed_includes == []


def test_clean_netlist_passes_through_unchanged_content():
    text = "v1 1 0 5\nr1 1 0 1k\n.op\n.end\n"
    res = sanitize_netlist(text)
    assert res.text == text
    assert res.removed_blocks == 0
    assert res.removed_includes == []


# ---------------------------------------------------------------------------
# Adversarial regressions: ngspice honors more file-splicing spellings than
# the original `_INCLUDE` pattern matched. These assert on the exact text
# handed to run_ngspice_text via core.evaluate_text(..., no_exec=True), which
# is what the MCP server and CI actually rely on for untrusted input. Each
# must fail before the shared-directive fix and pass after.
# ---------------------------------------------------------------------------
import pytest  # noqa: E402

from spiceguard import core  # noqa: E402


@pytest.fixture
def fake_ngspice(monkeypatch):
    """Capture the text handed to ngspice; pretend the sim succeeded."""
    captured = {}

    def fake_run(text, ngspice_path=None, cwd=None):
        captured["text"] = text
        return 0, "No. of Data Rows : 1\n"

    monkeypatch.setattr(core, "run_ngspice_text", fake_run)
    return captured


def _hostile_via(directive_line):
    """A netlist whose file-splicing directive line is immediately followed
    by a `.control` block — standing in for the shell-executing content that
    directive would splice in from the referenced file in a real ngspice run.
    """
    return (
        "v1 1 0 5\n"
        f"{directive_line}\n"
        ".control\n"
        "shell echo pwned\n"
        "run\n"
        ".endc\n"
        "r1 1 0 1k\n"
        ".end\n"
    )


def test_lib_directive_stripped_and_control_block_via_it_never_runs(fake_ngspice):
    core.evaluate_text(_hostile_via(".lib evil.lib section1"), no_exec=True)
    text = fake_ngspice["text"]
    assert ".lib" not in text.lower()
    assert "shell" not in text.lower()
    assert "run" not in text.lower()


def test_incl_directive_stripped_and_control_block_via_it_never_runs(fake_ngspice):
    core.evaluate_text(_hostile_via(".incl evil.cir"), no_exec=True)
    text = fake_ngspice["text"]
    assert ".incl" not in text.lower()
    assert "shell" not in text.lower()


def test_inclu_directive_stripped_and_control_block_via_it_never_runs(fake_ngspice):
    core.evaluate_text(_hostile_via(".inclu evil.cir"), no_exec=True)
    text = fake_ngspice["text"]
    assert ".inclu" not in text.lower()
    assert "shell" not in text.lower()


def test_includ_directive_stripped_and_control_block_via_it_never_runs(fake_ngspice):
    core.evaluate_text(_hostile_via(".includ evil.cir"), no_exec=True)
    text = fake_ngspice["text"]
    assert ".includ" not in text.lower()
    assert "shell" not in text.lower()


def test_lib_and_endl_lines_are_stripped_and_counted_in_removed_includes():
    text = (
        "v1 1 0 5\n"
        ".lib evil.lib section1\n"
        ".endl\n"
        "r1 1 0 1k\n"
        ".end\n"
    )
    res = sanitize_netlist(text)
    assert ".lib" not in res.text.lower()
    assert ".endl" not in res.text.lower()
    assert len(res.removed_includes) == 2


def test_incl_inclu_includ_prefix_forms_are_stripped():
    for directive in (".incl foo.cir", ".inclu foo.cir", ".includ foo.cir"):
        text = f"v1 1 0 5\n{directive}\nr1 1 0 1k\n.end\n"
        res = sanitize_netlist(text)
        assert directive.lower() not in res.text.lower(), (
            f"{directive!r} was not stripped: {res.text!r}"
        )
        assert res.removed_includes == [directive]
