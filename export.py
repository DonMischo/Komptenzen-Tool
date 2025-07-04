from __future__ import annotations
"""export.py – rev‑6
====================
Generate Lua + TeX files **and** compile new TeX files with *luatex*.

Directory layout stays:
    print_<YEAR>_{hj|ej}/<CLASS>/ lastname_firstname.{lua,tex,pdf}

Compilation
-----------
* Detect OS (Windows ⇒ MiKTeX, else ⇒ TeX Live) and call the first
  `luatex` found in *PATH*.
* Only TeX files **not previously compiled** are processed – basenames
  are cached in `.compiled` (one file per class dir).
* `export_students()` now returns `(lua_mapping, compiled_pdf_paths)` so
  the Admin UI can inform the user.
"""
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from sqlalchemy.orm import Session

from db_schema import (
    ENGINE,
    Student,
    Grade,
    SchoolYear,
    SchoolClass,
    ClassCompetence,
)

# ---------------------------------------------------------------------------
# Zeugnistext helper -------------------------------------------------------
# ---------------------------------------------------------------------------
def lua_long_str(s: str) -> str:
    """
    Wrap *s* in the shortest [=*[ … ]=*] delimiter that does not
    occur inside *s* itself.
    """
    for eq in range(0, 10):                     # usually 0 is enough
        open_  = "[" + "=" * eq + "["
        close_ = "]" + "=" * eq + "]"
        if open_ not in s and close_ not in s:
            return f"{open_}\n{s}\n{close_}"
    raise ValueError("text contains ]] with 9 ='s — very unlikely!")

def format_report_tex(text: str) -> str:
    """
    1. The first physical line (up to the first '\n') is taken as a greeting.
       → it becomes {\textbf{\LARGE …}}\\
    2. A single newline  ->  '\\\\'
       Two or more blank-line gaps  ->  '\\\\\n\\vspace{1em}'
    3. Everything after the greeting is prefixed with
       '\\nowidow[11]\\noclub[11]'
    """
    text = text.lstrip()                     # ignore leading blanks / BOM
    if "\n" in text:
        greeting, body = text.split("\n", 1)   # first line only
    else:
        greeting, body = text, ""

    # --- 1. greeting block ---
    formatted = rf"{{\textbf{{\LARGE {greeting.strip()} }}}}\\"

    if body:
        # --- 2. convert line breaks in the body ---
        # a) double (or more) newlines → \\  \vspace{1em}
        body = re.sub(r"\n{2,}",
                      r"\n \\vspace{1em}", body.strip())
        # b) remaining single newlines → \\
        body = body.replace("\n", r"\\")
        # --- 3. widows & clubs protection ---
        formatted += "\n\\nowidow[11]\\noclub[11]\\setstretch{1.15}\\large " + body

    return formatted


# ---------------------------------------------------------------------------
# Filename/dir helpers ------------------------------------------------------
# ---------------------------------------------------------------------------

def _slug(s: str) -> str:
    nfkd = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return "_".join("".join(c for c in nfkd.lower() if c.isalnum() or c == " ").split())


def _root_dir(sy: SchoolYear) -> Path:
    year = sy.report_day.year if sy.report_day else int(sy.name.split("/")[1])
    p = Path.cwd() / f"print_{year}_{'ej' if sy.endjahr else 'hj'}"
    p.mkdir(exist_ok=True)
    return p


def _copy_template(dst: Path) -> None:
    src = Path.cwd() / "TexTemplate"
    if not src.exists():
        raise FileNotFoundError("TexTemplate directory missing.")
    for item in src.iterdir():
        tgt = dst / item.name
        if not tgt.exists():
            if item.is_dir():
                shutil.copytree(item, tgt)
            else:
                shutil.copy2(item, tgt)


# ---------------------------------------------------------------------------
# Lua serializer (unchanged logic) ------------------------------------------
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Lua serializer (UNIVERSAL version)  ← REPLACE the old `_lua()` completely
# ---------------------------------------------------------------------------
def _lua(obj: Any, ind: int = 0) -> str:
    sp = " " * ind

    # tables ----------------------------------------------------------------
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        body = ",\n".join(
            f"{sp}  {k} = {_lua(v, ind + 2)}" for k, v in obj.items()
        )
        return f"{{\n{body},\n{sp}}}"
    if isinstance(obj, list):
        if not obj:
            return "{}"
        body = ",\n".join(_lua(v, ind + 2) for v in obj)
        return f"{{\n{body},\n{sp}}}"

    # strings ---------------------------------------------------------------
    if isinstance(obj, str):
        # any back-slash, newline, quote or “]]” ⇒ use long-bracket
        if ("\n" in obj) or ("\\" in obj) or ("'" in obj) or ("]]" in obj):
            return lua_long_str(obj)
        # simple case → single-quoted, escape single quote only
        # simple case → single-quoted, escape *only* the single quote itself
        return "'" + obj.replace("'", r"\'") + "'"


    # numbers / booleans / null --------------------------------------------
    return json.dumps(obj)



# ---------------------------------------------------------------------------
# Grade helper --------------------------------------------------------------
# ---------------------------------------------------------------------------

def _numeric_or_str(val: str | None) -> int | str | None:
    if val is None:
        return None
    txt = str(val).strip().replace(",", ".")
    try:
        num = float(txt)
        if num.is_integer() and 0 <= int(num) <= 9:
            return int(num)
    except ValueError:
        pass
    return txt


# ---------------------------------------------------------------------------
# Student → Lua + TeX -------------------------------------------------------
# ---------------------------------------------------------------------------

def _selected_comp_ids(ses: Session, class_row: SchoolClass) -> Set[int]:
    return {
        cc.competence_id
        for cc in ses.query(ClassCompetence)
                     .filter_by(class_id=class_row.id, selected=True)
                     .all()
    }


def _student_to_lua(stu: Student, sy: SchoolYear, sel_comp: Set[int], ses: Session) -> str:
    data: Dict[str, Any] = {
        "first_name": stu.first_name,
        "last_name": stu.last_name,
        "classRoom": stu.school_class.name if stu.school_class else "",
        "date_of_birth": stu.birthday.strftime("%d.%m.%Y"),
        "school_year": sy.name,
        "part_of_year": "Endjahr" if sy.endjahr else "Halbjahr",
        "report_date": sy.report_day.strftime("%d.%m.%Y") if sy.report_day else "",
        "personal_text": format_report_tex(stu.report_text) or "",
        "comment": stu.remarks or "",
        "absenceDaysTotal": stu.days_absent_excused + stu.days_absent_unexcused,
        "absenceDaysUnauthorized": stu.days_absent_unexcused,
        "absenceHoursTotal": stu.lessons_absent_excused + stu.lessons_absent_unexcused,
        "absenceHoursUnauthorized": stu.lessons_absent_unexcused,
        "lb": bool(stu.lb),
        "gb": bool(stu.gb),
        "subjects": [],
    }

    grade_map = {g.topic_id: _numeric_or_str(g.value) for g in ses.query(Grade).filter_by(student_id=stu.id)}

    for link in stu.subjects:
        subj = link.subject
        level_val = _numeric_or_str(link.niveau)
        topics_out = []
        if not stu.gb:
            for tp in subj.topics:
                if sel_comp and all(c.id not in sel_comp for c in tp.competences):
                    continue
                topics_out.append({
                    "title": tp.name,
                    "grade": grade_map.get(tp.id, ""),
                    "competences": [{"description": c.text} for c in tp.competences if not sel_comp or c.id in sel_comp],
                })
        data["subjects"].append({
            "name": subj.name,
            "level": level_val if level_val is not None else "",
            "topics": [] if stu.gb else topics_out,
        })
    return "student = " + _lua(data) + "\n return student\n"


def _write_student_files(stu: Student, sy: SchoolYear, cl_dir: Path, template: str, sel_comp: Set[int], ses: Session) -> str:
    base = f"{_slug(stu.last_name)}_{_slug(stu.first_name)}"
    lua_p = cl_dir / f"{base}.lua"
    tex_p = cl_dir / f"{base}.tex"
    lua_p.write_text(_student_to_lua(stu, sy, sel_comp, ses), encoding="utf-8")
    tex_p.write_text(template.replace("studentdata", base), encoding="utf-8")
    return base


# ---------------------------------------------------------------------------
# TeX compilation -----------------------------------------------------------
# ---------------------------------------------------------------------------
def _lualatex_exe() -> str:                     # ← rename
    return "lualatex.exe" if sys.platform.startswith("win") else "lualatex"

def _compile_tex(class_dir: Path, base: str) -> Path:
    tex = class_dir / f"{base}.tex"
    pdf = tex.with_suffix(".pdf")
    if not tex.exists():
        return pdf
    cmd = [
        _lualatex_exe(),                        # ← use lualatex
        "-interaction=nonstopmode",
        "-halt-on-error",
        tex.name,
    ]
    subprocess.run(cmd, cwd=class_dir, check=True,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return pdf


def _compile_new(class_dir: Path, basenames: List[str]) -> List[Path]:
    cache = class_dir / ".compiled"
    done: Set[str] = set(cache.read_text().splitlines()) if cache.exists() else set()
    compiled: List[Path] = []
    for base in basenames:
        if base in done:
            continue
        try:
            pdf = _compile_tex(class_dir, base)
            compiled.append(pdf)
            done.add(base)
        except subprocess.CalledProcessError as e:
            print(f"luatex failed for {base}:", e.stderr.decode(errors="ignore"))
    cache.write_text("\n".join(sorted(done)))
    return compiled

def _compile_selected(class_dir: Path, basenames: List[str]) -> List[Path]:
    cache = class_dir / ".compiled"
    done: Set[str] = set(cache.read_text().splitlines()) if cache.exists() else set()
    compiled: List[Path] = []

    for base in basenames:
        try:
            pdf = _compile_tex(class_dir, base)
            compiled.append(pdf)
            done.add(base)
        except subprocess.CalledProcessError as err:
            print(f"lualatex failed for {base}:\n", err.stderr.decode(errors="ignore"))

    cache.write_text("\n".join(sorted(done)))
    return compiled


# ---------------------------------------------------------------------------
# Public API ----------------------------------------------------------------
# ---------------------------------------------------------------------------

def export_students(student_ids: List[int], classroom: str) -> Tuple[Dict[str, str], List[Path]]:
    """Generate Lua/TeX, compile new TeX. Return (lua_map, compiled_pdfs)."""
    with Session(ENGINE) as ses:
        sy = ses.query(SchoolYear).order_by(SchoolYear.id.desc()).first()
        if not sy:
            raise RuntimeError("No SchoolYear row found")
        class_row = ses.query(SchoolClass).filter_by(name=classroom).first()
        if not class_row:
            raise RuntimeError(f"Klasse {classroom} nicht gefunden")

        sel_comp = _selected_comp_ids(ses, class_row)

        root = _root_dir(sy)
        _copy_template(root)
        cl_dir = root / classroom
        cl_dir.mkdir(exist_ok=True)
        template_tex = (root / "Zeugnis.tex").read_text(encoding="utf-8")

        lua_map: Dict[str, str] = {}
        bases: List[str] = []
        for stu in ses.query(Student).filter(Student.id.in_(student_ids)):
            base = _write_student_files(stu, sy, cl_dir, template_tex, sel_comp, ses)
            bases.append(base)
            lua_map[base] = str(cl_dir / f"{base}.lua")

        compiled = _compile_selected(cl_dir, bases)
        return lua_map, compiled


if __name__ == "__main__":
    m, pdf = export_students([], "5a")
    print(len(m), "Lua", len(pdf), "PDF built")
