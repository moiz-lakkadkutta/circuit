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
