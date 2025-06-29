# helpers.py
# ----------------------------------------------------
"""Kleine Streamlit-Utilities – momentan nur für eindeutige Widget-Keys."""

import re
import uuid
import streamlit as st

def unique_key(*parts: str, idx: int | None = None) -> str:
    """
    Baut aus beliebigen Teil­strings einen garantiert eindeutigen Key
    für Streamlit-Widgets.

    Beispiele
    ---------
    unique_key("Deutsch", "5/6", "Leseverstehen", idx=3)
    →  "Deutsch_5_6_Leseverstehen_3"
    """
    key = "_".join(_safe(p) for p in parts if p)
    if idx is not None:
        key = f"{key}_{idx}"
    return key or uuid.uuid4().hex        # Fallback – unique random

def _safe(s) -> str:                    # Typ weglassen oder Any
    """Ersetzt Nicht-Alphanumerisches, damit der Key gültig bleibt."""
    return re.sub(r"\W+", "_", str(s))   # ← cast auf String
    
    
def safe_rerun() -> None:
    """Kompatibler Seiten-Reload für alte + neue Streamlit-Versionen."""
    if hasattr(st, "experimental_rerun"):          # v1.2 …
        st.experimental_rerun()
    elif hasattr(st, "rerun"):                     # v1.26 …
        st.rerun()
    else:                                          # sehr alte Version
        # primitive Notlösung: Hinweis + Stop
        st.warning("Bitte Seite manuell neu laden (F5)")
        st.stop()