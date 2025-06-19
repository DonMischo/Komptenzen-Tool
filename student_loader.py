# student_loader.py
# ---------------------------------------------------------------
"""
CSV-Synchronisation für Schülerdaten.
Erwartet eine einzige Datei  students.csv  im Projekt­ordner.

CSV-Spalten (UTF-8, Header wichtig):
    ,Nachname,Vorname,Klasse,Geburtsdatum

Optionale Felder (werden, falls vorhanden, direkt übernommen):
    Fehltage,Fehltage Unentschuldigt,Fehlstunden,
    Fehlstunden Unentschuldigt,Zeugnistext,Bemerkungen
"""

from __future__ import annotations
import csv
from pathlib import Path
from datetime import datetime
from typing   import Dict, Set

from sqlalchemy.orm import Session

from db_schema   import ENGINE, Student
from db_helpers  import _get_or_create_class   # bereits vorhanden

CSV_FILE = Path("student_data/students.csv")                # zentraler Pfad

# ---------------------------------------------------------------
def _parse_date(raw: str) -> date:
    """
    Akzeptiert  dd.mm.yyyy   yyyy-mm-dd   und  dd.mm.yy  (→ 20yy).
    """
    raw = raw.strip()
    try:                                  # 1) dd.mm.yyyy
        return datetime.strptime(raw, "%d.%m.%Y").date()
    except ValueError:
        pass
    try:                                  # 2) yyyy-mm-dd
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        pass
    # 3) dd.mm.yy   →  dd.mm.20yy   (alle Geburten ab 2000)
    try:
        d = datetime.strptime(raw, "%d.%m.%y")          # Jahr zweistellig
        if d.year < 100:                                # safety-net
            d = d.replace(year=d.year + 2000)           #  ’04’ → 2004
        return d.date()
    except ValueError:
        raise ValueError(f"Ungültiges Geburtsdatum: {raw!r}")
        
def _read_csv(path: Path) -> list[Dict]:
    """Liest students.csv und gibt nur valide Zeilen zurück."""
    with path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    return [r for r in rows if r.get("Nachname", "").strip()]

# ---------------------------------------------------------------
def sync_students(remove_missing: bool = False) -> None:
    """
    Vergleicht CSV mit DB:
      • neue Schüler → insert
      • bestehende → update (Namen, Klasse, Geburtstag, Zeugnis­felder)
      • optional entfernte Schüler löschen
    """
    if not CSV_FILE.exists():
        print("⚠️  students.csv nicht gefunden – Sync übersprungen")
        return

    csv_rows = _read_csv(CSV_FILE)
    processed_ids: Set[int] = set()

    with Session(ENGINE) as ses:
        for row in csv_rows:
            # Klasse anlegen / holen
            cl = _get_or_create_class(ses, row["Klasse"].strip())

            # Schüler anhand (Nachname, Vorname, Geb.-Datum) identifizieren
            bday = _parse_date(row["Geburtsdatum"])
            stu = (
                ses.query(Student)
                .filter_by(
                    last_name=row["Nachname"].strip(),
                    first_name=row["Vorname"].strip(),
                    birthday=bday,
                )
                .first()
            )
            if stu is None:
                stu = Student(
                    last_name=row["Nachname"].strip(),
                    first_name=row["Vorname"].strip(),
                    birthday=bday,
                )
                ses.add(stu)

            # immer aktuelle Klasse setzen/aktualisieren
            stu.school_class = cl

            # optionale Felder übernehmen (falls vorhanden)
            stu.days_absent_excused      = int(row.get("Fehltage", 0))
            stu.days_absent_unexcused    = int(row.get("Fehltage Unentschuldigt", 0))
            stu.lessons_absent_excused   = int(row.get("Fehlstunden", 0))
            stu.lessons_absent_unexcused = int(row.get("Fehlstunden Unentschuldigt", 0))
            stu.report_text              = row.get("Zeugnistext", "").strip()
            stu.remarks                  = row.get("Bemerkungen", "").strip()

            processed_ids.add(stu.id)

        # Schüler löschen, die nicht mehr in der CSV stehen
        if remove_missing:
            ses.query(Student)\
               .filter(~Student.id.in_(processed_ids))\
               .delete(synchronize_session=False)

        ses.commit()
    print(f"✔ Schüler-Sync abgeschlossen ({len(processed_ids)} Datensätze verarbeitet)")

# ---------------------------------------------------------------
if __name__ == "__main__":
    sync_students(remove_missing=False)
