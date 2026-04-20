# student_loader.py
from __future__ import annotations
import csv
import io
from pathlib import Path
from datetime import date, datetime
from typing import Dict, List, Set, Tuple

from sqlalchemy.orm import Session
from db_schema import ENGINE, Student
from db_helpers import _get_or_create_class

CSV_FILE = Path("student_data/students.csv")


def _parse_date(raw: str) -> date:
    raw = raw.strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            pass
    try:
        d = datetime.strptime(raw, "%d.%m.%y")
        if d.year < 100:
            d = d.replace(year=d.year + 2000)
        return d.date()
    except ValueError:
        raise ValueError(f"Ungültiges Geburtsdatum: {raw!r}")


def _parse_rows(text: str) -> List[Dict]:
    rows = list(csv.DictReader(io.StringIO(text)))
    return [r for r in rows if r.get("Nachname", "").strip()]


def _sync_rows(rows: List[Dict], remove_missing: bool = True) -> Tuple[int, int, int]:
    """
    Synchronise DB students against a list of parsed CSV rows.
    Returns (added, updated, removed).
    """
    added = updated = removed = 0

    with Session(ENGINE) as ses:
        processed_ids: Set[int] = set()

        for row in rows:
            cl   = _get_or_create_class(ses, row["Klasse"].strip())
            bday = _parse_date(row["Geburtsdatum"])
            stu  = ses.query(Student).filter_by(
                last_name=row["Nachname"].strip(),
                first_name=row["Vorname"].strip(),
                birthday=bday,
            ).first()

            if stu is None:
                stu = Student(
                    last_name=row["Nachname"].strip(),
                    first_name=row["Vorname"].strip(),
                    birthday=bday,
                )
                ses.add(stu)
                added += 1
            else:
                updated += 1

            stu.school_class              = cl
            stu.days_absent_excused       = int(row.get("Fehltage", 0) or 0)
            stu.days_absent_unexcused     = int(row.get("Fehltage Unentschuldigt", 0) or 0)
            stu.lessons_absent_excused    = int(row.get("Fehlstunden", 0) or 0)
            stu.lessons_absent_unexcused  = int(row.get("Fehlstunden Unentschuldigt", 0) or 0)
            stu.report_text               = row.get("Zeugnistext", "").strip()
            stu.remarks                   = row.get("Bemerkungen", "").strip()

            ses.flush()  # ensure stu.id is populated
            processed_ids.add(stu.id)

        if remove_missing:
            to_delete = (
                ses.query(Student)
                .filter(Student.id.notin_(processed_ids))
                .all()
            )
            removed = len(to_delete)
            for s in to_delete:
                ses.delete(s)

        ses.commit()

    print(f"✔ Schüler-Sync: +{added} neu, ~{updated} aktualisiert, -{removed} entfernt")
    return added, updated, removed


def sync_students(remove_missing: bool = False) -> Tuple[int, int, int]:
    """Sync from the default CSV file on disk."""
    if not CSV_FILE.exists():
        print("⚠️  students.csv nicht gefunden – Sync übersprungen")
        return 0, 0, 0
    with CSV_FILE.open(encoding="utf-8", newline="") as fh:
        text = fh.read()
    rows = _parse_rows(text)
    return _sync_rows(rows, remove_missing=remove_missing)


def sync_students_from_upload(csv_bytes: bytes, remove_missing: bool = True) -> Tuple[int, int, int]:
    """Sync from uploaded CSV bytes (e.g. from st.file_uploader)."""
    text = csv_bytes.decode("utf-8", errors="replace")
    rows = _parse_rows(text)
    return _sync_rows(rows, remove_missing=remove_missing)


def count_students() -> int:
    with Session(ENGINE) as ses:
        return ses.query(Student).count()


if __name__ == "__main__":
    sync_students(remove_missing=False)
