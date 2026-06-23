"""html_to_latex.py — convert TipTap HTML to LaTeX.

Design constraint: output must work inside tabularray cells (X[l] columns)
as well as in normal document flow.  Therefore NO block-level environments
(\begin{itemize}, \begin{center}, \begin{tabular} …) are emitted — they
break tabularray's row scanner.  All structure is expressed with \par,
\textbullet, \hangindent, {\centering …} etc.

Supported elements
  Inline:  strong/b  em/i  u  s/strike/del  code  a  br  sup  sub
  Block:   p (with text-align)  h1 h2 h3 h4
  Lists:   ul  ol  li  (nested, ol with counters)
  Table:   table / tr / td|th  → tblr (tabularray, already loaded)
  Fallback: legacy plain-text (not starting with "<")
"""
from __future__ import annotations
import re
from html.parser import HTMLParser

# ---------------------------------------------------------------------------
# Character escaping
# ---------------------------------------------------------------------------

_SPECIAL = str.maketrans({
    "&":  r"\&",
    "%":  r"\%",
    "$":  r"\$",
    "#":  r"\#",
    "_":  r"\_",
    "{":  r"\{",
    "}":  r"\}",
    "~":  r"\textasciitilde{}",
    "^":  r"\textasciicircum{}",
    "\\": r"\textbackslash{}",
})


def _esc(t: str) -> str:
    return t.translate(_SPECIAL)


# ---------------------------------------------------------------------------
# HTML → LaTeX converter
# ---------------------------------------------------------------------------

class _Conv(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._out:    list[str] = []
        self._stack:  list[str] = []
        # paragraph buffer (collect content before we know alignment)
        self._pbuf:   list[str] | None = None
        self._palign: str | None = None
        # table state
        self._cbuf:   list[str] | None = None
        self._row:    list[str] = []
        self._trows:  list[list[str]] = []
        self._thead:  list[list[str]] = []
        self._tcols:  int = 0
        self._in_head: bool = False
        # ordered-list counter stack (one entry per nesting level)
        self._ol_counters: list[int] = []

    # ---- active write target -----------------------------------------------

    def _buf(self) -> list[str]:
        if self._cbuf is not None:
            return self._cbuf
        if self._pbuf is not None:
            return self._pbuf
        return self._out

    # ---- helpers -----------------------------------------------------------

    def _in_list(self) -> bool:
        return any(t in ("ul", "ol") for t in self._stack)

    # ---- SAX callbacks -----------------------------------------------------

    def handle_starttag(self, tag: str, attrs: list) -> None:
        self._stack.append(tag)
        ad = dict(attrs)

        # --- paragraph ---
        if tag == "p":
            self._pbuf = []
            m = re.search(r"text-align:\s*(\w+)", ad.get("style", ""))
            self._palign = m.group(1) if m else None

        # --- inline formatting ---
        elif tag in ("strong", "b"):
            self._buf().append(r"\textbf{")
        elif tag in ("em", "i"):
            self._buf().append(r"\textit{")
        elif tag == "u":
            self._buf().append(r"\underline{")
        elif tag in ("s", "strike", "del"):
            self._buf().append(r"\sout{")
        elif tag == "code":
            self._buf().append(r"\texttt{")
        elif tag == "sup":
            self._buf().append(r"\textsuperscript{")
        elif tag == "sub":
            self._buf().append(r"\textsubscript{")
        elif tag == "a":
            pass  # just output link text, ignore href

        # --- headings ---
        elif tag in ("h1", "h2"):
            self._buf().append(r"\textbf{\large ")
        elif tag in ("h3", "h4"):
            self._buf().append(r"\textbf{")

        # --- line break ---
        elif tag == "br":
            # \newline avoids tabularray row-separator interpretation of \\
            self._buf().append("\\newline\n")

        # --- lists ---
        # No \begin{itemize}/\begin{enumerate} — these break tabularray cells.
        # Each <li> opens a hanging-indent paragraph instead.
        elif tag == "ul":
            pass  # structure handled per <li>
        elif tag == "ol":
            self._ol_counters.append(0)

        elif tag == "li":
            if "ol" in self._stack:
                self._ol_counters[-1] += 1
                n = self._ol_counters[-1]
                self._out.append(
                    f"\n\\par\\noindent"
                    f"\\hangindent=1.5em\\hangafter=1 {n}.\\enspace "
                )
            else:
                self._out.append(
                    "\n\\par\\noindent"
                    "\\hangindent=1.5em\\hangafter=1 \\textbullet\\enspace "
                )

        # --- table ---
        elif tag == "table":
            self._trows, self._thead, self._tcols = [], [], 0
        elif tag == "thead":
            self._in_head = True
        elif tag == "tbody":
            self._in_head = False
        elif tag == "tr":
            self._row = []
        elif tag in ("td", "th"):
            self._cbuf = []

    def handle_endtag(self, tag: str) -> None:
        if self._stack and self._stack[-1] == tag:
            self._stack.pop()

        # --- paragraph ---
        if tag == "p":
            txt   = "".join(self._pbuf or [])
            align = self._palign
            self._pbuf, self._palign = None, None
            if align == "center":
                # {\centering …\par} works inside tabularray; \begin{center} does not
                self._out.append(f"\n{{\\centering {txt}\\par}}\n")
            elif align == "right":
                self._out.append(f"\n{{\\raggedleft {txt}\\par}}\n")
            else:
                self._out.append(f"\n{txt}\n")

        # --- inline closing brace ---
        elif tag in ("strong", "b", "em", "i", "u", "s", "strike", "del",
                      "code", "sup", "sub", "h1", "h2", "h3", "h4"):
            self._buf().append("}")

        # --- lists end: close the last hanging paragraph ---
        elif tag in ("ul", "ol"):
            self._out.append("\n\\par\n")
            if tag == "ol" and self._ol_counters:
                self._ol_counters.pop()

        # --- table cells / rows ---
        elif tag in ("td", "th"):
            self._row.append("".join(self._cbuf or []))
            self._cbuf = None
            if len(self._row) > self._tcols:
                self._tcols = len(self._row)
        elif tag == "tr":
            if self._in_head:
                self._thead.append(self._row)
            else:
                self._trows.append(self._row)
            self._row = []
        elif tag == "thead":
            self._in_head = False
        elif tag == "table":
            self._emit_table()

    def handle_data(self, data: str) -> None:
        # Skip whitespace-only text nodes produced by TipTap's HTML indentation.
        # They would create blank lines (\par) before \item / list content.
        if not data.strip():
            return
        self._buf().append(_esc(data))

    # ---- table emitter -----------------------------------------------------

    def _emit_table(self) -> None:
        all_rows = self._thead + self._trows
        if not all_rows:
            return
        cols = self._tcols or max((len(r) for r in all_rows), default=1)

        # Build tblr (tabularray) — safe for nesting; avoids \begin{tabular}
        # which conflicts with \\ row separators in the outer tabularray scan.
        colspec = " ".join(["X[l]"] * cols)
        lines: list[str] = [
            f"\\begin{{tblr}}{{width=\\linewidth,"
            f"colspec={{{colspec}}},hlines,vlines}}"
        ]
        if self._thead:
            for ri, row in enumerate(self._thead):
                row = row + [""] * (cols - len(row))
                cells = " & ".join(
                    f"\\textbf{{{c}}}" if c else "" for c in row
                )
                lines.append(cells + r" \\")
        for row in self._trows:
            row = row + [""] * (cols - len(row))
            lines.append(" & ".join(row) + r" \\")
        lines.append("\\end{tblr}")
        self._out.append("\n" + "\n".join(lines) + "\n")

    # ---- result ------------------------------------------------------------

    def latex(self) -> str:
        raw = "".join(self._out)
        collapsed = re.sub(r"\n{3,}", "\n\n", raw).strip()
        # str.replace not re.sub: re.sub interprets \\ as one backslash in the
        # replacement, producing \ instead of \\ (the LaTeX line-break command).
        return collapsed.replace("\n\n", "\\par\\vspace{.5em}").replace("\n", " ")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def html_to_latex(html: str) -> str:
    """Convert TipTap HTML to LaTeX safe for tabularray cells and document flow.

    If *html* does not look like HTML (legacy plain text stored before the
    rich-text editor was introduced) it is escaped and paragraph/line breaks
    are converted to LaTeX equivalents.
    """
    if not html:
        return ""
    if not html.strip().startswith("<"):
        # Legacy plain-text path
        import textwrap
        txt = textwrap.dedent(html).strip()
        txt = re.sub(r"\n{2,}", r"\\vspace{1em}", txt)
        return txt.replace("\n", r"\\")
    c = _Conv()
    c.feed(html)
    return c.latex()
