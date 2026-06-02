"""html_to_latex.py — convert Tiptap HTML output to LaTeX markup.

Handles bold, italic, underline, text alignment, bullet/ordered lists,
and tables.  Falls back to plain-text escaping for legacy non-HTML content.
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
        # paragraph buffer: collect paragraph content before we know the alignment
        self._pbuf:   list[str] | None = None
        self._palign: str | None = None
        # table state
        self._cbuf:   list[str] | None = None   # current cell buffer
        self._row:    list[str] = []
        self._trows:  list[list[str]] = []
        self._tcols:  int = 0
        self._in_tbl: bool = False

    # ---- active write target -----------------------------------------------

    def _buf(self) -> list[str]:
        if self._cbuf is not None:
            return self._cbuf
        if self._pbuf is not None:
            return self._pbuf
        return self._out

    # ---- SAX callbacks -----------------------------------------------------

    def handle_starttag(self, tag: str, attrs: list) -> None:
        self._stack.append(tag)
        ad = dict(attrs)

        if tag == "p":
            self._pbuf = []
            m = re.search(r"text-align:\s*(\w+)", ad.get("style", ""))
            self._palign = m.group(1) if m else None

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

        elif tag == "ul":
            self._out.append("\n\\begin{itemize}\n")
        elif tag == "ol":
            self._out.append("\n\\begin{enumerate}\n")
        elif tag == "li":
            self._out.append("\\item ")

        elif tag == "br":
            # Use \newline instead of \\ to avoid tabularray row-separator interception
            self._buf().append("\\newline\n")

        elif tag in ("h1", "h2"):
            self._buf().append(r"\textbf{\large ")
        elif tag == "h3":
            self._buf().append(r"\textbf{")

        elif tag == "table":
            self._in_tbl = True
            self._trows, self._tcols = [], 0
        elif tag == "tr":
            self._row = []
        elif tag in ("td", "th"):
            self._cbuf = []

    def handle_endtag(self, tag: str) -> None:
        if self._stack and self._stack[-1] == tag:
            self._stack.pop()

        if tag == "p":
            txt   = "".join(self._pbuf or [])
            align = self._palign
            self._pbuf, self._palign = None, None
            if align == "center":
                self._out.append(f"\n\\begin{{center}}\n{txt}\n\\end{{center}}\n")
            elif align == "right":
                self._out.append(f"\n\\begin{{flushright}}\n{txt}\n\\end{{flushright}}\n")
            else:
                self._out.append(f"\n{txt}\n")

        elif tag in ("strong", "b", "em", "i", "u", "s", "strike", "del",
                      "h1", "h2", "h3", "code"):
            self._buf().append("}")

        elif tag == "ul":
            self._out.append("\\end{itemize}\n")
        elif tag == "ol":
            self._out.append("\\end{enumerate}\n")

        elif tag in ("td", "th"):
            self._row.append("".join(self._cbuf or []))
            self._cbuf = None
            if len(self._row) > self._tcols:
                self._tcols = len(self._row)
        elif tag == "tr":
            self._trows.append(self._row)
            self._row = []
        elif tag == "table":
            self._in_tbl = False
            self._emit_table()

    def handle_data(self, data: str) -> None:
        # Skip whitespace-only text nodes (TipTap indents its HTML with
        # spaces/newlines between tags that would otherwise create \par
        # before the first \item and trigger a LaTeX error).
        if not data.strip():
            return
        self._buf().append(_esc(data))

    # ---- table emitter -----------------------------------------------------

    def _emit_table(self) -> None:
        if not self._trows:
            return
        cols = self._tcols or max((len(r) for r in self._trows), default=1)
        spec = "|" + "|".join(["l"] * cols) + "|"
        lines = [f"\\begin{{tabular}}{{{spec}}}", "\\hline"]
        for row in self._trows:
            row = row + [""] * (cols - len(row))
            lines.append(" & ".join(row) + r" \\")
            lines.append("\\hline")
        lines.append("\\end{tabular}")
        self._out.append("\n" + "\n".join(lines) + "\n")

    # ---- result ------------------------------------------------------------

    def latex(self) -> str:
        raw = "".join(self._out)
        return re.sub(r"\n{3,}", "\n\n", raw).strip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def html_to_latex(html: str) -> str:
    """Convert Tiptap HTML to LaTeX.

    If *html* does not look like HTML (legacy plain-text stored before the
    rich-text editor was introduced) it is escaped and newlines are converted
    to LaTeX line-breaks so existing reports keep rendering correctly.
    """
    if not html:
        return ""
    if not html.strip().startswith("<"):
        # Legacy plain text path
        import textwrap
        txt = textwrap.dedent(html).strip()
        txt = re.sub(r"\n{2,}", r"\\vspace{1em}", txt)
        return txt.replace("\n", r"\\")
    c = _Conv()
    c.feed(html)
    return c.latex()
