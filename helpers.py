# helpers.py
# ----------------------------------------------------
"""Kleine Streamlit-Utilities – momentan nur für eindeutige Widget-Keys."""

import re
import uuid
import streamlit as st
from db_schema import Topic
from typing import Any

def unique_key(*parts: Any) -> str:
    """
    Build a stable key from arbitrary parts.

    * If one of the parts is a Topic object → use its primary-key.
    * Otherwise: cast each part to str and join with '|'.

    Works for:
        unique_key("subject_select")             # 1 arg
        unique_key(subject_name, topic)          # 2 args (old use-case)
    """
    norm: list[str] = []
    for p in parts:
        if isinstance(p, Topic):
            norm.append(str(p.id))
        else:
            norm.append(str(p))
    return "|".join(norm)


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