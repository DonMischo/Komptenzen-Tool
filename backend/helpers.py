# Stub that shadows app/helpers.py — removes the streamlit dependency
# for the FastAPI backend.

def unique_key(*parts) -> str:
    return "|".join(str(p.id if hasattr(p, "id") else p) for p in parts)

def safe_rerun() -> None:
    pass
