from __future__ import annotations
"""export.py – rev‑8 (syntax‑fixed)
===================================
* Keeps all logic from rev‑7 *plus* LB long‑text handling.
* Fixes the stray ``if long_level_text`` (missing colon) that caused the
  SyntaxError.
* `_compile_selected` now **always** recompiles the basenames passed in
  (fresh PDFs every click) and then updates `.compiled` purely as
  history.
"""

import json
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import select

from db_schema import (
    ENGINE,
    Student,
    Grade,
    SchoolYear,
    SchoolClass,
    ClassCompetence,
    Subject,
)

# ---------------------------------------------------------------------------
# Helpers / filenames -------------------------------------------------------
# ---------------------------------------------------------------------------

def _slug(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return "_".join("".join(c for c in nfkd.lower() if c.isalnum() or c == " ").split())


def _root_dir(sy: SchoolYear) -> Path:
    year = sy.report_day.year if sy.report_day else int(sy.name.split("/")[1])
    d = Path.cwd() / f"print_{year}_{'ej' if sy.endjahr else 'hj'}"
    d.mkdir(exist_ok=True)
    return d


def _copy_template(dst: Path) -> None:
    src = Path.cwd() / "TexTemplate"
    if not src.exists():
        raise FileNotFoundError("TexTemplate directory missing.")
    for itm in src.iterdir():
        tgt = dst / itm.name
        if not tgt.exists():
            shutil.copytree(itm, tgt) if itm.is_dir() else shutil.copy2(itm, tgt)

# ---------------------------------------------------------------------------
# Lua serializer ------------------------------------------------------------
# ---------------------------------------------------------------------------

def _lua(obj: Any, ind: int = 0) -> str:
    sp = " " * ind
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        body = ",\n".join(f"{sp}  {k} = {_lua(v, ind+2)}" for k, v in obj.items())
        return f"{{\n{body},\n{sp}}}"
    if isinstance(obj, list):
        if not obj:
            return "{}"
        body = ",\n".join(_lua(v, ind+2) for v in obj)
        return f"{{\n{body},\n{sp}}}"
    if isinstance(obj, str):
        esc = obj.replace("'", "\\'")
        return f"'{esc}'"
    return json.dumps(obj)

# ---------------------------------------------------------------------------
# Grade helper --------------------------------------------------------------
# ---------------------------------------------------------------------------

def _numeric_or_str(val: str | None) -> int | str | None:
    if val is None:
        return None
    txt = str(val).strip().replace(",", ".")
    try:
        f = float(txt)
        if f.is_integer() and 0 <= int(f) <= 9:
            return int(f)
    except ValueError:
        pass
    return txt

# ---------------------------------------------------------------------------
# Text helpers for level long‑text -----------------------------------------
# ---------------------------------------------------------------------------

def _latex_escape_body(txt: str) -> str:
    # replace blank lines with vspace and single breaks with \
    import re, textwrap
    txt = textwrap.dedent(txt).strip()
    txt = re.sub(r"\n{2,}", r"\\vspace{1em}", txt)
    return txt.replace("\n", r"\\")


def format_level_text(txt: str) -> str:
    return r"\makecell[l]{\setstretch{1.15}\large " + _latex_escape_body(txt) + "}"

# ---------------------------------------------------------------------------
# Student → Lua -------------------------------------------------------------
# ---------------------------------------------------------------------------

def _selected_comp_ids(ses: Session, class_row: SchoolClass) -> Set[int]:
    return {
        cc.competence_id
        for cc in ses.query(ClassCompetence)
                     .filter_by(class_id=class_row.id, selected=True)
                     .all()
    }


def _has_grade(subj: Subject, grade_map: Dict[int, Any]) -> bool:
    return any(grade_map.get(tp.id) not in (None, "", " ") for tp in subj.topics)


def _student_to_lua(stu: Student, sy: SchoolYear, sel_comp: Set[int], ses: Session) -> str:
    data: Dict[str, Any] = {
        "first_name": stu.first_name,
        "last_name": stu.last_name,
        "classRoom": stu.school_class.name if stu.school_class else "",
        "date_of_birth": stu.birthday.strftime("%d.%m.%Y"),
        "school_year": sy.name,
        "part_of_year": "Endjahr" if sy.endjahr else "Halbjahr",
        "report_date": sy.report_day.strftime("%d.%m.%Y") if sy.report_day else "",
        "personal_text": stu.report_text or "",
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

    want_wp = stu.school_class.name.startswith("7")

    for link in stu.subjects:
        subj = link.subject
        raw_level = link.niveau.strip() if link.niveau else ""
        long_level_text = len(raw_level) > 3
        level_val: Any = format_level_text(raw_level) if long_level_text else _numeric_or_str(raw_level)
        has_grade = _has_grade(subj, grade_map)

        if want_wp and not (has_grade or raw_level):
            continue

        export_comp = not stu.gb and not long_level_text
        topics_out: List[Dict[str, Any]] = []
        if export_comp:
            for tp in subj.topics:
                if sel_comp and all(c.id not in sel_comp for c in tp.competences):
                    continue
                topics_out.append({
                    "title": tp.name,
                    "grade": grade_map.get(tp.id, ""),
                    "competences": [
                        {"description": c.text} for c in tp.competences
                        if not sel_comp or c.id in sel_comp
                    ],
                })

        data["subjects"].append({
            "name": subj.name,
            "level": level_val if level_val is not None else "",
            "topics": [] if stu.gb else topics_out,
        })

    return "student = " + _lua(data) + "\n"

# ---------------------------------------------------------------------------
# File + TeX generation -----------------------------------------------------
# ---------------------------------------------------------------------------

def _write_student_files(stu: Student, sy: SchoolYear, cl_dir: Path, template: str,
                         sel_comp: Set[int], ses: Session) -> str:
    base = f"{_slug(stu.last_name)}_{_slug(stu.first_name)}"
    (cl_dir / f"{base}.lua").write_text(_student_to_lua(stu, sy, sel_comp, ses), encoding="utf-8")
    (cl_dir / f"{base}.tex").write_text(template.replace("studentdata.lua", f"{base}.lua"), encoding="utf-8")
    return base

# ---------------------------------------------------------------------------
# TeX compilation -----------------------------------------------------------
# ---------------------------------------------------------------------------

def _lualatex_exe() -> str:
    return "lualatex.exe" if sys.platform.startswith("win") else "lualatex"


def _compile_tex(class_dir: Path, base: str) -> Path:
    tex = class_dir / f"{base}.tex"
    pdf = tex.with_suffix(".pdf")
    if not tex.exists():
        return pdf
    cmd = [_lualatex_exe(), "-interaction=nonstopmode", "-halt-on-error", tex.name]
    subprocess.run(cmd, cwd=class_dir, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return pdf


def _compile_selected(class_dir: Path, basenames: List[str]) -> List[Path]:
    cache = class_dir / ".compiled"
    done: Set[str] = set(cache.read_text().splitlines()) if cache.exists() else set()
    compiled: List[Path] = []

    for base in basenames:
        # always compile fresh
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
    """Generate Lua/TeX for given students and compile new PDFs.
    Returns (lua_path_map, compiled_pdf_paths)."""
    with Session(ENGINE) as ses:
        sy = ses.query(SchoolYear).order_by(SchoolYear.id.desc()).first()
        if not sy:
            raise RuntimeError("No SchoolYear row found")
        class_row = ses.query(SchoolClass).filter_by(name=classroom).first()
        if not class_row:
            raise RuntimeError(f"Class {classroom} not found")

        sel_comp = _selected_comp_ids(ses, class_row)

        root = _root_dir(sy)
        _copy_template(root)
        cl_dir = root / classroom
        cl_dir.mkdir(exist_ok=True)
        template_tex = (root / "Zeugnis.tex").read_text(encoding="utf-8")

        lua_map: Dict[str, str] = {}
        bases: List[str] = []
        for stu in (
            ses.query(Student)
            .filter(Student.id.in_(student_ids))
            .order_by(Student.last_name, Student.first_name)
        ):
            base = _write_student_files(stu, sy, cl_dir, template_tex, sel_comp, ses)
            bases.append(base)
            lua_map[base] = str(cl_dir / f"{base}.lua")

        compiled = _compile_selected(cl_dir, bases)
        return lua_map, compiled


if __name__ == "__main__":
    m, pdfs = export_students([], "5a")
    print(len(m), "Lua files", len(pdfs), "PDF built")
