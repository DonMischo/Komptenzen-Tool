"""export.py – clean version (rev‑4)
===================================
Exports each selected student as a Lua data file plus a TeX wrapper using the
school’s *Zeugnis.tex* template. This version fixes the duplicate function
header that caused a *SyntaxError* and passes the SQLAlchemy session through
all helper calls.
"""
from __future__ import annotations

import json
import shutil
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Set

from sqlalchemy.orm import Session

from db_schema import (
    ENGINE,
    Student,
    Grade,
    StudentSubject,
    SchoolYear,
    SchoolClass,
    ClassCompetence,
)

# ---------------------------------------------------------------------------
# Utility helpers -----------------------------------------------------------
# ---------------------------------------------------------------------------

def _slug(text: str) -> str:
    """Return an ASCII‑only, lower‑case filename slug."""
    nfkd = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return "_".join("".join(c for c in nfkd.lower() if c.isalnum() or c == " ").split())


def _root_dir(sy: SchoolYear) -> Path:
    year_num = sy.report_day.year if sy.report_day else int(sy.name.split("/")[1])
    root = Path.cwd() / f"print_{year_num}_{'ej' if sy.endjahr else 'hj'}"
    root.mkdir(exist_ok=True)
    return root


def _copy_template(dst: Path) -> None:
    """Copy ./TexTemplate into *dst* (skip already existing files)."""
    src = Path.cwd() / "TexTemplate"
    if not src.exists():
        raise FileNotFoundError("TexTemplate directory missing.")
    for item in src.iterdir():
        tgt = dst / item.name
        if not tgt.exists():
            shutil.copytree(item, tgt) if item.is_dir() else shutil.copy2(item, tgt)


# ---------------------------------------------------------------------------
# Lua serializer ------------------------------------------------------------
# ---------------------------------------------------------------------------

def _lua(obj: Any, ind: int = 0) -> str:
    sp = " " * ind
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        parts = [sp + "{"]
        for k, v in obj.items():
            parts.append(f"{sp}  {k} = {_lua(v, ind + 2)},")
        parts.append(sp + "}")
        return "\n".join(parts)
    if isinstance(obj, list):
        if not obj:
            return "{}"
        parts = [sp + "{"]
        for v in obj:
            parts.append(f"{_lua(v, ind + 2)},")
        parts.append(sp + "}")
        return "\n".join(parts)
    if isinstance(obj, str):
        s = obj.replace("'", "\\'")
        return f"'{s}'" if "\n" not in s else f"[[\n{s}\n{sp}]]"
    return json.dumps(obj)


# ---------------------------------------------------------------------------
# Domain helpers ------------------------------------------------------------
# ---------------------------------------------------------------------------
def _numeric_or_str(val: str | None) -> int | str | None:
    """Return an int 0-9 if *val* looks like 0, 1, … 9 (also '1.0', '1,0')."""
    if val is None:
        return None

    v = str(val).strip().replace(",", ".")    #  '1,0' → '1.0'
    try:
        num = float(v)
        if num.is_integer() and 0 <= int(num) <= 9:
            return int(num)
    except ValueError:
        pass                                   # not a number at all

    return v                                   # keep original string



def _selected_competence_ids(ses: Session, class_row: SchoolClass) -> Set[int]:
    return {
        cc.competence_id
        for cc in ses.query(ClassCompetence)
                     .filter_by(class_id=class_row.id, selected=True)
                     .all()
    }


# ---------------------------------------------------------------------------
# Student → Lua -------------------------------------------------------------
# ---------------------------------------------------------------------------

def _build_student_lua(
    stu: Student,
    sy: SchoolYear,
    sel_comp: Set[int],
    ses: Session,
) -> str:
    """Return complete Lua source for one student."""

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

    # fresh grade map from DB
    grade_map = {
        g.topic_id: _numeric_or_str(g.value)
        for g in ses.query(Grade).filter_by(student_id=stu.id).all()
    }

    wahlpflicht_added = False

    for link in stu.subjects:
        subj = link.subject
        is_wp = subj.name.startswith("Wahlpflichtbereich")
        if is_wp and wahlpflicht_added:
            continue

        level_val = _numeric_or_str(link.niveau)
        topics_out: List[Dict[str, Any]] = []

        if not stu.gb:
            for top in subj.topics:
                comps = [c for c in top.competences if not sel_comp or c.id in sel_comp]
                if not comps:
                    continue
                topics_out.append(
                    {
                        "title": top.name,
                        "grade": grade_map.get(top.id, ""),
                        "competences": [{"description": c.text} for c in comps],
                    }
                )

        # LB verbal rule
        if stu.lb and isinstance(level_val, str) and len(level_val) > 2:
            topics_out = []

        # skip Wahlpflicht without output
        if is_wp and not (level_val or any(t["grade"] for t in topics_out) or topics_out):
            continue

        data["subjects"].append(
            {
                "name": subj.name,
                "level": level_val if level_val is not None else "",
                "topics": [] if stu.gb else topics_out,
            }
        )
        if is_wp:
            wahlpflicht_added = True

    return "student = " + _lua(data) + "\n"


# ---------------------------------------------------------------------------
# File writers --------------------------------------------------------------
# ---------------------------------------------------------------------------

def _write_files(
    stu: Student,
    sy: SchoolYear,
    class_dir: Path,
    template_tex: str,
    sel_comp: Set[int],
    ses: Session,
) -> str:
    base = f"{_slug(stu.last_name)}_{_slug(stu.first_name)}"
    lua_path = class_dir / f"{base}.lua"
    tex_path = class_dir / f"{base}.tex"

    lua_path.write_text(_build_student_lua(stu, sy, sel_comp, ses), encoding="utf-8")
    tex_path.write_text(template_tex.replace("studentdata.lua", lua_path.name), encoding="utf-8")
    return str(lua_path)


# ---------------------------------------------------------------------------
# Public entry --------------------------------------------------------------
# ---------------------------------------------------------------------------

def export_students(student_ids: List[int], classroom: str) -> Dict[str, str]:
    """Generate Lua + TeX files; return mapping «basename → lua_abs_path»."""
    with Session(ENGINE) as ses:
        sy = ses.query(SchoolYear).order_by(SchoolYear.id.desc()).first()
        if not sy:
            raise RuntimeError("No SchoolYear row found.")

        class_row = ses.query(SchoolClass).filter_by(name=classroom).first()
        if class_row is None:
            raise RuntimeError(f"Klasse '{classroom}' nicht gefunden.")

        sel_comp = _selected_competence_ids(ses, class_row)

        root = _root_dir(sy)
        _copy_template(root)

        class_dir = root / classroom
        class_dir.mkdir(exist_ok=True)
        template_tex = (root / "Zeugnis.tex").read_text(encoding="utf-8")

        mapping: Dict[str, str] = {}
        for stu in ses.query(Student).filter(Student.id.in_(student_ids)).all():
            key = f"{_slug(stu.last_name)}_{_slug(stu.first_name)}"
            mapping[key] = _write_files(stu, sy, class_dir, template_tex, sel_comp, ses)
        return mapping


if __name__ == "__main__":
    print("Run export_students([...], '5a') from the Admin UI.")
