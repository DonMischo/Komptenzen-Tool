#!/usr/bin/env python3
"""
populate_random_reports.py
──────────────────────────
Populates the database with **random demo data** for every student
and offers verbose output so you can track progress.

Updates in this version
=======================
• **Niveau (level) rules**
    – LB‑students → "LB" for every subject  
    – GB‑students → "GB" for every subject  
    – Subjects with no level (Werkstätten, Darstellen u. Gestalten) → ""  
    – Everyone else → random "1", "2" or "3"

• **Absence data**  
    Generates realistic numbers:  
    days_excused 0‑10, days_unexcused ≤ ⅓ of excused,  
    lessons derived from the days (× 4‑6).

Run with
```
python populate_random_reports.py --db db/reports_2024-2025_ej.db
```
Pass `--seed N` for reproducible data.
"""

import argparse
import random
import textwrap
from pathlib import Path
from typing import List, Dict

from sqlalchemy import select
from sqlalchemy.orm import Session

# --- project‑internal imports ------------------------------------------------
import db_schema as db
from db_schema import (
    Base,
    Student,
    SchoolClass,
    Subject,
    Topic,
    Competence,
    ClassCompetence,
    Grade,
    StudentSubject,
)

# ──────────────────────────────────────────────────────────────────────────────
#  configuration helpers
# ──────────────────────────────────────────────────────────────────────────────
CLASS_SUBJECTS: Dict[int, List[str]] = {
    5: [
        "Deutsch", "Mathematik", "Englisch",
        "Technisches Werken", "Geografie",
        "Geschichte", "Evangelische Religionslehre",
        "Sport", "Werkstätten", "Mitarbeit und Verhalten",
    ],
    6: [
        "Deutsch", "Mathematik", "Englisch",
        "MNT - Projekt Lutherpark", "Technisches Werken",
        "Geografie", "Geschichte", "Evangelische Religionslehre",
        "Sport", "Werkstätten", "Mitarbeit und Verhalten",
    ],
    7: [
        "Deutsch", "Mathematik", "Englisch",
        "Wahlpflichtbereich - Französisch", "Wahlpflichtbereich - Spanisch",
        "Wahlpflichtbereich - Darstellen und Gestalten",
        "Wahlpflichtbereich - Natur und Technik",
        "MNT - Projekt Lutherpark",
        "Technisches Werken", "Geografie",
        "Chemie", "Physik", "Biologie",
        "Geschichte", "Evangelische Religionslehre",
        "Sport", "Werkstätten", "Mitarbeit und Verhalten",
    ],
}

NO_LEVEL_SUBJECTS = {
    "Werkstätten",
    "Wahlpflichtbereich - Darstellen und Gestalten",
}

GRADE_VALUES = ["1", "2", "3", "4", "nb", ""]


def lorem_ipsum(words: int = 150) -> str:
    """Return *words* random lorem‑ipsum words."""
    base = (
        "lorem ipsum dolor sit amet consectetur adipiscing elit "
        "sed do eiusmod tempor incididunt ut labore et dolore magna "
        "aliqua ut enim ad minim veniam quis nostrud exercitation "
        "ullamco laboris nisi ut aliquip ex ea commodo consequat duis "
        "aute irure dolor in reprehenderit in voluptate velit esse "
        "cillum dolore eu fugiat nulla pariatur excepteur sint occaecat "
        "cupidatat non proident sunt in culpa qui officia deserunt mollit "
        "anim id est laborum"
    ).split()

    bag = []
    while len(bag) < words:
        bag.extend(random.sample(base, len(base)))
    return (" ".join(bag[:words]).capitalize() + ".")


def random_absences() -> dict:
    """Return a dict with random absence numbers (excused > unexcused)."""
    days_exc = random.randint(0, 10)
    days_un  = random.randint(0, max(1, days_exc // 3))
    lessons_exc = days_exc * random.randint(4, 6)
    lessons_un  = days_un  * random.randint(4, 6)
    return dict(
        days_excused=days_exc,
        days_unexcused=days_un,
        lessons_excused=lessons_exc,
        lessons_unexcused=lessons_un,
    )


# ──────────────────────────────────────────────────────────────────────────────
#  core logic
# ──────────────────────────────────────────────────────────────────────────────
def populate(session: Session) -> None:
    for school_class in session.scalars(select(SchoolClass)).all():
        try:
            grade_num = int(school_class.name[0])
        except (ValueError, TypeError):
            continue
        if grade_num not in (5, 6, 7):
            continue

        students = list(school_class.students)
        if not students:
            continue

        print(f"\n=== Class {school_class.name} ({len(students)} students) ===")

        # choose LB + GB
        lb_student, gb_student = random.sample(
            students, 2 if len(students) >= 2 else 1
        )
        lb_student.lb = True
        gb_student.gb = True
        print(f" → LB student: {lb_student.first_name} {lb_student.last_name} (id={lb_student.id})")
        print(f" → GB student: {gb_student.first_name} {gb_student.last_name} (id={gb_student.id})")

        # subjects for the whole class
        wanted_subjs = CLASS_SUBJECTS[grade_num]
        subjects = session.scalars(
            select(Subject).where(Subject.name.in_(wanted_subjs))
        ).all()
        subj_map = {s.name: s for s in subjects}

        # topic / competence selection
        for subj in subjects:
            block_key = "5/6" if grade_num in (5, 6) else "7/8"
            topics = [t for t in subj.topics if t.block == block_key]
            for topic in topics:
                comp_pool = topic.competences
                if not comp_pool:
                    continue
                chosen = random.sample(
                    comp_pool,
                    k=random.randint(1, min(3, len(comp_pool)))
                )

                # mark selection
                for comp in comp_pool:
                    cc = session.get(
                        ClassCompetence, (school_class.id, comp.id)
                    )
                    if cc is None:
                        cc = ClassCompetence(
                            class_id=school_class.id,
                            competence_id=comp.id,
                        )
                        session.add(cc)
                    cc.selected = comp in chosen

                if not chosen:
                    continue

                # grades per student
                for stu in students:
                    g = (
                        session.query(Grade)
                        .filter_by(student_id=stu.id, topic_id=topic.id)
                        .one_or_none()
                    )
                    if g is None:
                        g = Grade(student_id=stu.id, topic_id=topic.id)
                        session.add(g)
                    g.value = random.choice(GRADE_VALUES)

        # student‑level data
        for stu in students:
            print(f"   Processing student {stu.first_name} {stu.last_name} (id={stu.id})")
            for subj_name in wanted_subjs:
                subj = subj_map[subj_name]
                ss = (
                    session.query(StudentSubject)
                    .filter_by(student_id=stu.id, subject_id=subj.id)
                    .one_or_none()
                )
                if ss is None:
                    ss = StudentSubject(student_id=stu.id, subject_id=subj.id)
                    session.add(ss)

                # set niveau rules
                if stu.gb:
                    ss.niveau = "GB"
                elif stu.lb:
                    ss.niveau = "LB"
                elif subj.name in NO_LEVEL_SUBJECTS:
                    ss.niveau = ""
                else:
                    ss.niveau = random.choice(["1", "2", "3"])

            # report text
            stu.report_text = lorem_ipsum(150)

            # absence data
            absd = random_absences()
            stu.days_absent_excused      = absd["days_excused"]
            stu.days_absent_unexcused    = absd["days_unexcused"]
            stu.lessons_absent_excused   = absd["lessons_excused"]
            stu.lessons_absent_unexcused = absd["lessons_unexcused"]

            print(f"     Absence: {absd['days_excused']}+{absd['days_unexcused']} days "
                  f"({absd['lessons_excused']}+{absd['lessons_unexcused']} lessons)")

    session.commit()


# ──────────────────────────────────────────────────────────────────────────────
#  CLI
# ──────────────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(__doc__),
    )
    parser.add_argument(
        "-d", "--db", dest="db_path", default=db.DB_PATH, type=Path,
        help=f"SQLite file to use (default: {db.DB_PATH})",
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Seed RNG for reproducible output",
    )
    args = parser.parse_args()
    if args.seed is not None:
        random.seed(args.seed)

    # configure DB engine
    db.switch_engine(Path(args.db_path))
    db.init_db(populate=True)
    engine = db.ENGINE
    Base.metadata.create_all(engine)

    with Session(engine) as ses:
        populate(ses)

    print("\n✅  Random report data generated successfully.")


if __name__ == "__main__":
    main()
