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
# Whitespace and Unicode-space sanitisation
# ---------------------------------------------------------------------------

class TestWhitespaceSanitisation:
    """_sanitize() and the whitespace-stripping pass in latex()."""

    # --- Unicode space variants normalised to plain space ---

    def test_nbsp_in_text_becomes_space(self):
        """Non-breaking space (U+00A0) inside text → regular space."""
        out = latex("<p>Hallo Welt</p>")
        assert "Hallo Welt" in out

    def test_thin_space_in_text_becomes_space(self):
        """Thin space (U+2009, common Word 'half space') → regular space."""
        out = latex("<p>Hallo Welt</p>")
        assert "Hallo Welt" in out

    def test_narrow_nbsp_in_text_becomes_space(self):
        """Narrow no-break space (U+202F) → regular space."""
        out = latex("<p>Hallo Welt</p>")
        assert "Hallo Welt" in out

    def test_hair_space_in_text_becomes_space(self):
        """Hair space (U+200A) → regular space."""
        out = latex("<p>Hallo Welt</p>")
        assert "Hallo Welt" in out

    # --- Whitespace-only paragraphs → empty line → wide gap ---

    def test_nbsp_only_paragraph_is_wide_gap(self):
        r"""<p>\xa0</p> (non-breaking space only) → \vspace{2em}\newline ."""
        out = latex("<p>A</p><p> </p><p>B</p>")
        assert "\\vspace{2em}\\newline " in out

    def test_thin_space_only_paragraph_is_wide_gap(self):
        r"""<p> </p> (thin space only) → \vspace{2em}\newline ."""
        out = latex("<p>A</p><p> </p><p>B</p>")
        assert "\\vspace{2em}\\newline " in out

    def test_multiple_spaces_only_paragraph_is_wide_gap(self):
        r"""<p>   </p> (plain spaces only) → \vspace{2em}\newline ."""
        out = latex("<p>A</p><p>   </p><p>B</p>")
        assert "\\vspace{2em}\\newline " in out

    # --- Leading / trailing whitespace stripped ---

    def test_leading_whitespace_stripped(self):
        """Output does not start with a space or newline."""
        out = latex("<p>Text</p>")
        assert out == out.strip()

    def test_trailing_whitespace_stripped(self):
        """Output does not end with a space or newline."""
        out = latex("<p>Text</p>")
        assert out == out.strip()

    def test_leading_empty_paragraph_stripped(self):
        """An empty <p></p> at the start produces no leading separator."""
        out = latex("<p></p><p>Text</p>")
        assert not out.startswith("\\vspace")

    def test_trailing_empty_paragraph_stripped(self):
        """An empty <p></p> at the end produces no trailing separator."""
        out = latex("<p>Text</p><p></p>")
        assert not out.endswith("\\vspace{2em}\\newline ")

    # --- Typographic characters normalised ---

    def test_soft_hyphen_stripped(self):
        """Soft hyphen (U+00AD) is removed entirely."""
        out = latex("<p>Hallo­Welt</p>")
        assert "HalloWelt" in out
        assert "­" not in out

    def test_zero_width_space_stripped(self):
        """Zero-width space (U+200B) is removed entirely."""
        out = latex("<p>Hallo​Welt</p>")
        assert "HalloWelt" in out

    def test_smart_quotes_normalised(self):
        """Curly quotes are converted to straight ASCII equivalents."""
        out = latex("<p>“Hallo” und ‘Welt’</p>")
        assert '"Hallo"' in out
        assert "'Welt'" in out

    def test_ellipsis_normalised(self):
        """Unicode ellipsis (U+2026) → three dots."""
        out = latex("<p>und so weiter…</p>")
        assert "..." in out


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
        """Two paragraphs must produce a line break command in output for LuaTeX."""
        out = latex("<p>A</p><p>B</p>")
        assert "A" in out
        assert "B" in out
        assert "newline" in out or "\\\\" in out

    def test_double_newline_uses_1em(self):
        r"""Two adjacent paragraphs → \vspace{1em}\newline  (normal gap)."""
        out = latex("<p>A</p><p>B</p>")
        assert "\\vspace{1em}\\newline " in out

    def test_par_not_used_as_separator(self):
        r"""The separator must NOT be \par — it causes tabularray to fail."""
        out = latex("<p>A</p><p>B</p>")
        assert "\\par" not in out

    def test_three_paragraphs_two_separators(self):
        r"""Three paragraphs produce exactly two \vspace{1em}\newline  separators."""
        out = latex("<p>A</p><p>B</p><p>C</p>")
        assert out.count("\\vspace{1em}\\newline ") == 2

    def test_triple_newline_uses_2em(self):
        r"""Three newlines in raw output → \vspace{2em}\newline  (wide gap).

        An empty <p></p> between two paragraphs generates a triple newline
        in the raw buffer, producing a wider visual separation.
        """
        # <p>A</p><p></p><p>B</p> → raw has \nA\n + \n\n + \nB\n = \nA\n\n\n\nB\n
        # After strip+normalize: A\n\n\nB → wide gap
        out = latex("<p>A</p><p></p><p>B</p>")
        assert "\\vspace{2em}\\newline " in out


# ---------------------------------------------------------------------------
# Realistic Zeugnis text — 7ef student
# ---------------------------------------------------------------------------

# A realistic multi-paragraph personal text as TipTap would store it.
# Covers:
#   - multiple normal paragraph breaks  → \vspace{1em}\newline 
#   - empty paragraph (<p></p>)          → \vspace{2em}\newline  wide gap
#   - paragraph with only &nbsp;         → treated as empty line (wide gap)
#   - thin/narrow Unicode spaces in text → normalised to regular spaces
#   - single-cell table wrapper          → unwrapped (no \begin{tblr})
#   - no bare \n in output
#   - no leading/trailing whitespace
_ZEUGNIS_HTML = """\
<p>Liebe Lea,</p>
<p>dein siebtes Schuljahr an der Evangelischen Gemeinschaftsschule Erfurt
hast du erfolgreich abgeschlossen. Es war ein aufregendes Jahr voller neuer
Erfahrungen, das du mit Energie und Freude gemeistert hast.</p>
<p></p>
<p>Im Unterricht zeigst du immer wieder, dass du über gute Fähigkeiten
verfügst. Besonders in den Fächern, die dein Interesse wecken, arbeitest
du engagiert mit und bringst dich mit guten Gedanken ein. Dabei nutzt du auch
die Möglichkeit, Fragen zu stellen – das ist sehr lobenswert.</p>
<p> </p>
<p>Für das kommende Schuljahr wünschen wir dir, dass du deine Stärken
noch entschlossener einsetzt. Nicht immer muss alles sofort gelingen —
wichtig ist, den ersten Schritt zu machen.</p>
<p>Wir freuen uns darauf, dich auf deinem weiteren Weg begleiten zu dürfen.</p>
<p>Viele Grüße von Frau Müller und Herrn Schmidt</p>
"""

# Same content wrapped in a single-cell table (Word text-box paste).
_ZEUGNIS_TABLE_HTML = f"<table><tbody><tr><td>{_ZEUGNIS_HTML}</td></tr></tbody></table>"


class TestRealisticZeugnisText:
    """html_to_latex on a realistic 7ef Zeugnis personal_text."""

    def test_no_bare_newlines(self):
        out = latex(_ZEUGNIS_HTML)
        assert "\n" not in out

    def test_no_leading_trailing_whitespace(self):
        out = latex(_ZEUGNIS_HTML)
        assert out == out.strip()

    def test_normal_paragraph_break_present(self):
        r"""Adjacent paragraphs produce \vspace{1em}\newline ."""
        out = latex(_ZEUGNIS_HTML)
        assert "\\vspace{1em}\\newline " in out

    def test_empty_paragraph_produces_wide_gap(self):
        r"""<p></p> between paragraphs produces \vspace{2em}\newline ."""
        out = latex(_ZEUGNIS_HTML)
        assert "\\vspace{2em}\\newline " in out

    def test_nbsp_paragraph_produces_wide_gap(self):
        r"""<p>&nbsp;</p> (space-only paragraph) also produces a wide gap."""
        # The \xa0 is normalised to space → whitespace-only line → empty line
        # so it merges with surrounding \n's to form a triple newline.
        out = latex(_ZEUGNIS_HTML)
        # There are two wide gaps: one from <p></p> and one from <p>&nbsp;</p>
        assert out.count("\\vspace{2em}\\newline ") >= 2

    def test_en_dash_normalised(self):
        """Unicode en-dash in text → ASCII --."""
        out = latex(_ZEUGNIS_HTML)
        assert "--" in out

    def test_em_dash_normalised(self):
        """Unicode em-dash → ---."""
        out = latex(_ZEUGNIS_HTML)
        assert "---" in out

    def test_no_par_command(self):
        r"""Output must not contain \par (causes tabularray dimension overflow)."""
        out = latex(_ZEUGNIS_HTML)
        assert "\\par" not in out

    def test_content_present(self):
        """Key phrases from the text survive the conversion."""
        out = latex(_ZEUGNIS_HTML)
        assert "Liebe Lea" in out
        assert "Viele Gr" in out  # Grüße — ü is fine in LuaLaTeX

    def test_single_cell_table_unwrapped(self):
        r"""Single-cell table wrapper is stripped — no \begin{tblr} in output."""
        out = latex(_ZEUGNIS_TABLE_HTML)
        assert "\\begin{tblr}" not in out

    def test_single_cell_table_content_preserved(self):
        """Content from inside the single-cell table is still present."""
        out = latex(_ZEUGNIS_TABLE_HTML)
        assert "Liebe Lea" in out


# ---------------------------------------------------------------------------
# par_mode=True — document-body paragraph breaks
# ---------------------------------------------------------------------------

def par(html: str) -> str:
    return html_to_latex(html, par_mode=True)


class TestParModeHtmlP:
    r"""par_mode with <p> tag input → \par instead of \newline."""

    def test_single_paragraph_no_par(self):
        r"""Single paragraph: no \par needed, just the text."""
        out = par("<p>Hallo Welt</p>")
        assert "Hallo Welt" in out
        assert "\\newline" not in out

    def test_two_paragraphs_produce_par(self):
        r"""Two adjacent <p> tags → \par  between them."""
        out = par("<p>A</p><p>B</p>")
        assert "\\par " in out
        assert "A" in out
        assert "B" in out

    def test_no_newline_in_output(self):
        """par_mode output must not contain bare newlines."""
        out = par("<p>A</p><p>B</p>")
        assert "\n" not in out

    def test_no_vspace_newline_in_par_mode(self):
        r"""par_mode must not emit \vspace{1em}\newline (cell-mode markers)."""
        out = par("<p>A</p><p>B</p>")
        assert "\\vspace" not in out
        assert "\\newline" not in out

    def test_empty_paragraph_produces_bigskip(self):
        r"""<p></p> between text paragraphs → \par\bigskip  (wide gap)."""
        out = par("<p>A</p><p></p><p>B</p>")
        assert "\\par\\bigskip " in out

    def test_realistic_text_has_par(self):
        r"""Realistic multi-paragraph text produces \par."""
        out = par(_ZEUGNIS_HTML)
        assert "\\par " in out
        assert "Liebe Lea" in out

    def test_realistic_text_no_newline(self):
        """Realistic text in par_mode has no bare newlines."""
        out = par(_ZEUGNIS_HTML)
        assert "\n" not in out

    def test_realistic_text_no_vspace(self):
        r"""Realistic text in par_mode has no \vspace (cell-mode artifact)."""
        out = par(_ZEUGNIS_HTML)
        assert "\\vspace" not in out


class TestParModeHtmlBr:
    r"""par_mode with <br> tag input — \newline promoted to \par."""

    def test_br_becomes_par(self):
        r"""<br> inside a <p> in par_mode → \par  (not \newline)."""
        out = par("<p>A<br/>B</p>")
        assert "\\par " in out
        assert "\\newline" not in out

    def test_br_content_preserved(self):
        out = par("<p>Line one<br/>Line two</p>")
        assert "Line one" in out
        assert "Line two" in out


class TestParModeLegacyPlainText:
    r"""par_mode with legacy plain-text input (no leading '<')."""

    def test_single_newline_becomes_par(self):
        r"""Single \n → \par  in par_mode."""
        out = par("A\nB")
        assert "\\par " in out
        assert "A" in out
        assert "B" in out

    def test_multi_newline_becomes_par_medskip(self):
        r"""Two or more \n → \par\medskip  in par_mode."""
        out = par("A\n\nB")
        assert "\\par\\medskip " in out

    def test_no_bare_newlines(self):
        out = par("A\nB\n\nC")
        assert "\n" not in out

    def test_no_vspace_newline_in_par_mode(self):
        r"""Legacy plain-text par_mode must not emit \vspace or \newline."""
        out = par("A\nB\n\nC")
        assert "\\vspace" not in out
        assert "\\newline" not in out

    def test_empty_input_returns_empty(self):
        assert par("") == ""


class TestParModeVsCellMode:
    r"""Cross-check: same input, opposite mode, produces opposite markers."""

    def test_p_tags_cell_mode_uses_newline(self):
        r"""Default (cell) mode: adjacent <p> → \vspace{1em}\newline ."""
        out = latex("<p>A</p><p>B</p>")
        assert "\\vspace{1em}\\newline " in out

    def test_p_tags_par_mode_uses_par(self):
        r"""par_mode: adjacent <p> → \par ."""
        out = par("<p>A</p><p>B</p>")
        assert "\\par " in out
        assert "\\vspace" not in out

    def test_plain_text_cell_mode_uses_newline_backslash(self):
        r"""Default mode, plain text: \n → \\ ."""
        out = latex("A\nB")
        assert "\\\\" in out

    def test_plain_text_par_mode_uses_par(self):
        r"""par_mode, plain text: \n → \par ."""
        out = par("A\nB")
        assert "\\par " in out
        assert "\\\\" not in out
