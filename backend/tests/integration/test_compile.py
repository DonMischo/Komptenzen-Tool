"""Integration tests for the PDF compile pipeline.

Runs inside the Docker backend container where lualatex and all deps
are available. Tests:
- lualatex is callable and produces a PDF
- html_to_latex produces valid LaTeX output
- _lua serializer produces valid Lua table syntax
- export._slug normalises names correctly
"""
from __future__ import annotations

import subprocess
import textwrap
import tempfile
import os
from pathlib import Path

import pytest

from integration_helpers import requires_pg
from html_to_latex import html_to_latex
from export import _lua, _slug, _numeric_or_str


def _lualatex_available() -> bool:
    try:
        r = subprocess.run(["lualatex", "--version"], capture_output=True, timeout=5)
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


requires_latex = pytest.mark.skipif(
    not _lualatex_available(), reason="lualatex not available"
)


# ---------------------------------------------------------------------------
# lualatex compile
# ---------------------------------------------------------------------------

@requires_latex
class TestLualatexCompile:
    def _compile(self, tex: str) -> tuple[bool, str]:
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "doc.tex"
            src.write_text(tex, encoding="utf-8")
            r = subprocess.run(
                ["lualatex", "--interaction=nonstopmode", "doc.tex"],
                cwd=tmpdir, capture_output=True, text=True, timeout=30,
            )
            success = (Path(tmpdir) / "doc.pdf").exists()
            return success, r.stdout + r.stderr

    def test_minimal_document(self):
        ok, log = self._compile(
            r"\documentclass{article}\begin{document}Hello\end{document}"
        )
        assert ok, f"Compile failed:\n{log[:500]}"

    def test_unicode_in_document(self):
        ok, log = self._compile(textwrap.dedent(r"""
            \documentclass{article}
            \usepackage{fontspec}
            \begin{document}
            Müller, Straße, café
            \end{document}
        """))
        assert ok, f"Unicode compile failed:\n{log[:500]}"

    def test_latex_from_html_compiles(self):
        """Convert real HTML → LaTeX and verify it compiles."""
        html = (
            "<p>Anna zeigt <strong>sehr gute</strong> Leistungen.</p>"
            "<p>Sie arbeitet <em>zuverlässig</em> und selbstständig.</p>"
        )
        latex_body = html_to_latex(html)
        doc = textwrap.dedent(r"""
            \documentclass{article}
            \usepackage{fontspec}
            \begin{document}
        """) + latex_body + r"\end{document}"
        ok, log = self._compile(doc)
        assert ok, f"html→latex compile failed:\n{log[:500]}"


# ---------------------------------------------------------------------------
# html_to_latex
# ---------------------------------------------------------------------------

class TestHtmlToLatexIntegration:
    def test_bold_tag(self):
        assert r"\textbf{stark}" in html_to_latex("<strong>stark</strong>")

    def test_italic_tag(self):
        assert r"\textit{kursiv}" in html_to_latex("<em>kursiv</em>")

    def test_paragraph_break_no_bare_newline(self):
        result = html_to_latex("<p>Erste</p><p>Zweite</p>")
        assert "\n\n" not in result

    def test_paragraph_break_becomes_backslash_space(self):
        # html_to_latex emits \ (one backslash); _lua() doubles it to \\ for LaTeX
        result = html_to_latex("<p>A</p><p>B</p>")
        assert "\\" in result

    def test_special_chars_escaped(self):
        result = html_to_latex("<p>50% & mehr</p>")
        assert "\\%" in result
        assert "\\&" in result

    def test_empty_input(self):
        assert html_to_latex("") == ""

    def test_plain_text_passthrough(self):
        result = html_to_latex("Kein HTML hier")
        assert "Kein HTML hier" in result


# ---------------------------------------------------------------------------
# export helpers (pure — no latex needed)
# ---------------------------------------------------------------------------

class TestExportHelpersIntegration:
    def test_lua_dict(self):
        result = _lua({"name": "Müller", "grade": 3})
        assert "name = 'M" in result
        assert "grade = 3" in result

    def test_lua_empty_dict(self):
        assert _lua({}) == "{}"

    def test_lua_nested(self):
        result = _lua({"student": {"last_name": "Müller"}})
        assert "student = " in result
        assert "last_name = 'M" in result

    def test_lua_string_escapes_backslash(self):
        result = _lua("a\\b")
        assert "\\\\" in result

    def test_lua_string_escapes_newline(self):
        result = _lua("line1\nline2")
        assert "\\\\" in result
        assert "\n" not in result[1:-1]  # strip surrounding quotes

    def test_slug_simple(self):
        assert _slug("Max Müller") == "max_muller"

    def test_slug_special_chars_removed(self):
        assert _slug("A!B") == "ab"

    def test_numeric_or_str_grade(self):
        assert _numeric_or_str("3") == 3
        assert _numeric_or_str("10") == "10"
        assert _numeric_or_str(None) is None
        assert _numeric_or_str("3,5") == "3.5"
