"""test_html_to_latex.py — unit tests for html_to_latex.py.

Covers the public html_to_latex() function: HTML parsing, character escaping,
inline formatting, paragraph breaks, lists, and the legacy plain-text path.
"""
from __future__ import annotations

import pytest

from html_to_latex import html_to_latex


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def latex(html: str) -> str:
    return html_to_latex(html)


# ---------------------------------------------------------------------------
# Empty / non-HTML input
# ---------------------------------------------------------------------------

class TestEmptyInput:
    def test_empty_string(self):
        assert latex("") == ""

    def test_whitespace_only(self):
        # Not HTML, so goes through legacy path, strip should give ""
        assert latex("   ") == ""


# ---------------------------------------------------------------------------
# Character escaping
# ---------------------------------------------------------------------------

class TestCharacterEscaping:
    def test_ampersand(self):
        assert r"\&" in latex("<p>A &amp; B</p>")

    def test_percent(self):
        assert r"\%" in latex("<p>50%</p>")

    def test_dollar(self):
        assert r"\$" in latex("<p>$100</p>")

    def test_hash(self):
        assert r"\#" in latex("<p>#1</p>")

    def test_underscore(self):
        assert r"\_" in latex("<p>a_b</p>")

    def test_tilde(self):
        assert r"\textasciitilde{}" in latex("<p>~</p>")

    def test_caret(self):
        assert r"\textasciicircum{}" in latex("<p>^</p>")

    def test_backslash(self):
        assert r"\textbackslash{}" in latex("<p>\\</p>")


# ---------------------------------------------------------------------------
# Inline formatting
# ---------------------------------------------------------------------------

class TestInlineFormatting:
    def test_bold(self):
        out = latex("<p><strong>fett</strong></p>")
        assert r"\textbf{fett}" in out

    def test_bold_b_tag(self):
        out = latex("<p><b>fett</b></p>")
        assert r"\textbf{fett}" in out

    def test_italic(self):
        out = latex("<p><em>kursiv</em></p>")
        assert r"\textit{kursiv}" in out

    def test_italic_i_tag(self):
        out = latex("<p><i>kursiv</i></p>")
        assert r"\textit{kursiv}" in out

    def test_underline(self):
        out = latex("<p><u>unterstrichen</u></p>")
        assert r"\underline{unterstrichen}" in out

    def test_strikethrough(self):
        out = latex("<p><s>durch</s></p>")
        assert r"\sout{durch}" in out

    def test_code(self):
        out = latex("<p><code>x = 1</code></p>")
        assert r"\texttt{x = 1}" in out

    def test_superscript(self):
        out = latex("<p>x<sup>2</sup></p>")
        assert r"\textsuperscript{2}" in out

    def test_subscript(self):
        out = latex("<p>H<sub>2</sub>O</p>")
        assert r"\textsubscript{2}" in out

    def test_nested_bold_italic(self):
        out = latex("<p><strong><em>fett kursiv</em></strong></p>")
        assert r"\textbf{" in out
        assert r"\textit{" in out
        assert "fett kursiv" in out

    def test_link_text_only(self):
        out = latex('<p><a href="https://example.com">Klick mich</a></p>')
        assert "Klick mich" in out
        assert "href" not in out
        assert "example.com" not in out


# ---------------------------------------------------------------------------
# Headings
# ---------------------------------------------------------------------------

class TestHeadings:
    def test_h1(self):
        out = latex("<h1>Titel</h1>")
        assert r"\textbf{\large Titel}" in out

    def test_h2(self):
        out = latex("<h2>Untertitel</h2>")
        assert r"\textbf{\large Untertitel}" in out

    def test_h3(self):
        out = latex("<h3>Abschnitt</h3>")
        assert r"\textbf{Abschnitt}" in out

    def test_h4(self):
        out = latex("<h4>Klein</h4>")
        assert r"\textbf{Klein}" in out


# ---------------------------------------------------------------------------
# Paragraphs and alignment
# ---------------------------------------------------------------------------

class TestParagraphs:
    def test_plain_paragraph(self):
        out = latex("<p>Hallo Welt</p>")
        assert "Hallo Welt" in out

    def test_centered_paragraph(self):
        out = latex('<p style="text-align: center;">Mitte</p>')
        assert r"{\centering" in out
        assert "Mitte" in out

    def test_right_aligned(self):
        out = latex('<p style="text-align: right;">Rechts</p>')
        assert r"{\raggedleft" in out
        assert "Rechts" in out

    def test_paragraph_break_becomes_double_backslash(self):
        out = latex("<p>Erster Absatz</p><p>Zweiter Absatz</p>")
        # The LaTeX line-break command is \\ (two chars: backslash backslash)
        assert "\\" in out

    def test_br_becomes_newline_command(self):
        out = latex("<p>Zeile 1<br>Zeile 2</p>")
        assert r"\newline" in out


# ---------------------------------------------------------------------------
# Lists
# ---------------------------------------------------------------------------

class TestLists:
    def test_unordered_list_bullet(self):
        out = latex("<ul><li>Punkt A</li><li>Punkt B</li></ul>")
        assert r"\textbullet" in out
        assert "Punkt A" in out
        assert "Punkt B" in out

    def test_ordered_list_numbers(self):
        out = latex("<ol><li>Erstens</li><li>Zweitens</li></ol>")
        assert "1." in out
        assert "2." in out
        assert "Erstens" in out

    def test_list_uses_hangindent(self):
        out = latex("<ul><li>X</li></ul>")
        assert r"\hangindent" in out

    def test_list_no_begin_itemize(self):
        out = latex("<ul><li>X</li></ul>")
        assert r"\begin{itemize}" not in out

    def test_ordered_list_no_begin_enumerate(self):
        out = latex("<ol><li>X</li></ol>")
        assert r"\begin{enumerate}" not in out


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

class TestTables:
    def test_table_becomes_tblr(self):
        html = (
            "<table><tbody>"
            "<tr><td>A</td><td>B</td></tr>"
            "</tbody></table>"
        )
        out = latex(html)
        assert r"\begin{tblr}" in out
        assert r"\end{tblr}" in out
        assert "A" in out
        assert "B" in out

    def test_table_header_bold(self):
        html = (
            "<table><thead><tr><th>Kopf</th></tr></thead>"
            "<tbody><tr><td>Inhalt</td></tr></tbody></table>"
        )
        out = latex(html)
        assert r"\textbf{Kopf}" in out

    def test_table_no_begin_tabular(self):
        html = "<table><tbody><tr><td>X</td></tr></tbody></table>"
        out = latex(html)
        assert r"\begin{tabular}" not in out


# ---------------------------------------------------------------------------
# Legacy plain-text path
# ---------------------------------------------------------------------------

class TestLegacyPlainText:
    def test_plain_text_passed_through(self):
        out = latex("Einfacher Text ohne HTML")
        assert "Einfacher Text ohne HTML" in out

    def test_plain_text_newlines_become_backslash(self):
        out = latex("Zeile 1\nZeile 2")
        assert r"\\" in out

    def test_plain_text_double_newlines(self):
        out = latex("Para 1\n\nPara 2")
        assert r"\vspace{1em}" in out

    def test_plain_text_special_char_not_escaped(self):
        # Legacy path does NOT escape LaTeX specials — it's for pre-escaped text
        out = latex("Score: 50%")
        assert "50%" in out


# ---------------------------------------------------------------------------
# Paragraph break survival through Lua serialisation
# ---------------------------------------------------------------------------

class TestParagraphBreakEscaping:
    def test_output_contains_no_bare_newlines(self):
        """After latex(), all \n should be gone (replaced with \\ or space)."""
        out = latex("<p>Erster Absatz</p><p>Zweiter Absatz</p>")
        assert "\n" not in out

    def test_single_newlines_removed(self):
        """Single \n inside output is collapsed to space."""
        out = latex("<p>Text</p>")
        assert "\n" not in out

    def test_double_backslash_present_for_para_break(self):
        """Two paragraphs must produce \\ (LaTeX line break) in output for LuaTeX."""
        out = latex("<p>A</p><p>B</p>")
        assert "\\" in out
        assert "A" in out
        assert "B" in out
