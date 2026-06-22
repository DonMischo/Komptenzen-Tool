# student_loader.py
from __future__ import annotations
import csv
import io
from pathlib import Path
from datetime import date, datetime
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy.orm import Session
from db_schema import ENGINE, Student
from db_helpers import _get_or_create_class

CSV_FILE = Path("student_data/students.csv")

# Fields the caller may ask to update.  Absent from the set → field is skipped.
ALL_UPDATE_FIELDS = {"klasse", "fehltage", "zeugnistext", "bemerkungen"}

# Human-readable labels used in diff output
_FIELD_LABELS = {
    "klasse":       "Klasse",
    "fehltage":     "Fehlzeiten",
    "zeugnistext":  "Zeugnistext",
    "bemerkungen":  "Bemerkungen",
}


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


def _decode_csv(raw: bytes) -> str:
    """Decode CSV bytes trying common Windows/Excel encodings in order."""
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("latin-1")  # always succeeds


def _detect_dialect(text: str) -> type:
    """Use csv.Sniffer to detect delimiter and quoting style from the first 4 KB."""
    try:
        return csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
    except csv.Error:
        return csv.excel  # fallback: standard comma-separated


def _parse_rows(text: str) -> List[Dict]:
    dialect = _detect_dialect(text)
    rows = list(csv.DictReader(io.StringIO(text), dialect=dialect))
    return [r for r in rows if r.get("Nachname", "").strip()]


def _safe_int(val, default: int = 0) -> int:
    try:
        return int(val or default)
    except (ValueError, TypeError):
        return default


def _fehltage_str(stu: Student) -> str:
    return (
        f"T.e.={stu.days_absent_excused} T.u.={stu.days_absent_unexcused} "
        f"S.e.={stu.lessons_absent_excused} S.u.={stu.lessons_absent_unexcused}"
    )


def _fehltage_from_row(row: Dict) -> Tuple[int, int, int, int]:
    return (
        _safe_int(row.get("Fehltage", 0)),
        _safe_int(row.get("Fehltage Unentschuldigt", 0)),
        _safe_int(row.get("Fehlstunden", 0)),
        _safe_int(row.get("Fehlstunden Unentschuldigt", 0)),
    )


# ---------------------------------------------------------------------------
# Preview (dry-run, no DB writes)
# ---------------------------------------------------------------------------

def compute_diff(
    rows: List[Dict],
    remove_missing: bool,
    update_fields: Set[str],
) -> dict:
    """
    Compare CSV rows against the current DB and return a structured diff.
    Does NOT commit anything.

    Returns a dict matching StudentPreviewResponse schema.
    """
    to_add: list[dict] = []
    to_update: list[dict] = []
    to_remove: list[dict] = []
    unchanged = 0
    errors: list[str] = []

    with Session(ENGINE) as ses:
        processed_ids: Set[int] = set()

        for row in rows:
            name = f"{row.get('Vorname','').strip()} {row.get('Nachname','').strip()}"
            try:
                bday = _parse_date(row["Geburtsdatum"])
            except (ValueError, KeyError) as e:
                errors.append(f"{name}: ungültiges Geburtsdatum – {e}")
                continue

            csv_class = row.get("Klasse", "").strip()
            stu = ses.query(Student).filter_by(
                last_name=row["Nachname"].strip(),
                first_name=row["Vorname"].strip(),
                birthday=bday,
            ).first()

            if stu is None:
                to_add.append({
                    "name": name.strip(),
                    "school_class": csv_class,
                    "action": "add",
                    "changes": [],
                })
                continue

            processed_ids.add(stu.id)
            changes: list[dict] = []

            # --- Klasse ---
            if "klasse" in update_fields:
                db_class = stu.school_class.name if stu.school_class else ""
                if csv_class and db_class != csv_class:
                    changes.append({"field": "Klasse", "old": db_class, "new": csv_class})

            # --- Fehlzeiten ---
            if "fehltage" in update_fields:
                te, tu, se, su = _fehltage_from_row(row)
                db_str = _fehltage_str(stu)
                new_str = f"T.e.={te} T.u.={tu} S.e.={se} S.u.={su}"
                if db_str != new_str:
                    changes.append({"field": "Fehlzeiten", "old": db_str, "new": new_str})

            # --- Zeugnistext ---
            if "zeugnistext" in update_fields:
                csv_text = row.get("Zeugnistext", "").strip()
                db_text = (stu.report_text or "").strip()
                if csv_text != db_text:
                    changes.append({
                        "field": "Zeugnistext",
                        "old": db_text[:80] + ("…" if len(db_text) > 80 else ""),
                        "new": csv_text[:80] + ("…" if len(csv_text) > 80 else ""),
                    })

            # --- Bemerkungen ---
            if "bemerkungen" in update_fields:
                csv_bem = row.get("Bemerkungen", "").strip()
                db_bem = (stu.remarks or "").strip()
                if csv_bem != db_bem:
                    changes.append({
                        "field": "Bemerkungen",
                        "old": db_bem[:80] + ("…" if len(db_bem) > 80 else ""),
                        "new": csv_bem[:80] + ("…" if len(csv_bem) > 80 else ""),
                    })

            if changes:
                to_update.append({
                    "name": name.strip(),
                    "school_class": csv_class or (stu.school_class.name if stu.school_class else ""),
                    "action": "update",
                    "changes": changes,
                })
            else:
                unchanged += 1

        if remove_missing:
            missing = (
                ses.query(Student)
                .filter(Student.id.notin_(processed_ids))
                .all()
            )
            for s in missing:
                to_remove.append({
                    "name": f"{s.first_name} {s.last_name}",
                    "school_class": s.school_class.name if s.school_class else "",
                    "action": "remove",
                    "changes": [],
                })

    return {
        "to_add": to_add,
        "to_update": to_update,
        "to_remove": to_remove,
        "unchanged": unchanged,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# Apply sync
# ---------------------------------------------------------------------------

def _sync_rows(
    rows: List[Dict],
    remove_missing: bool = True,
    update_fields: Optional[Set[str]] = None,
) -> Tuple[int, int, int, list]:
    """
    Synchronise DB students against parsed CSV rows.

    update_fields controls which fields may be overwritten on existing students.
    Default (None) → all fields.  Only non-empty CSV values are written.
    Returns (added, updated, removed, skipped_errors).
    """
    if update_fields is None:
        update_fields = ALL_UPDATE_FIELDS

    added = updated = removed = 0

    with Session(ENGINE) as ses:
        processed_ids: Set[int] = set()
        errors: list[str] = []

        for row in rows:
            name = f"{row.get('Vorname','').strip()} {row.get('Nachname','').strip()}"
            try:
                bday = _parse_date(row["Geburtsdatum"])
            except (ValueError, KeyError) as e:
                errors.append(f"{name}: ungültiges Geburtsdatum – {e}")
                continue

            csv_class = row.get("Klasse", "").strip()
            stu = ses.query(Student).filter_by(
                last_name=row["Nachname"].strip(),
                first_name=row["Vorname"].strip(),
                birthday=bday,
            ).first()

            if stu is None:
                cl = _get_or_create_class(ses, csv_class)
                stu = Student(
                    last_name=row["Nachname"].strip(),
                    first_name=row["Vorname"].strip(),
                    birthday=bday,
                    school_class=cl,
                )
                ses.add(stu)
                added += 1
            else:
                updated += 1

                if "klasse" in update_fields and csv_class:
                    stu.school_class = _get_or_create_class(ses, csv_class)

                if "fehltage" in update_fields:
                    te, tu, se, su = _fehltage_from_row(row)
                    stu.days_absent_excused      = te
                    stu.days_absent_unexcused    = tu
                    stu.lessons_absent_excused   = se
                    stu.lessons_absent_unexcused = su

                if "zeugnistext" in update_fields:
                    csv_text = row.get("Zeugnistext", "").strip()
                    if csv_text:  # never blank out existing text
                        stu.report_text = csv_text

                if "bemerkungen" in update_fields:
                    csv_bem = row.get("Bemerkungen", "").strip()
                    if csv_bem:  # never blank out existing remarks
                        stu.remarks = csv_bem

            ses.flush()
            processed_ids.add(stu.id)

        if errors:
            print(f"⚠️  {len(errors)} Zeile(n) übersprungen: {'; '.join(errors)}")

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
    return added, updated, removed, errors


def sync_students(remove_missing: bool = False) -> Tuple[int, int, int]:
    """Sync from the default CSV file on disk."""
    if not CSV_FILE.exists():
        print("⚠️  students.csv nicht gefunden – Sync übersprungen")
        return 0, 0, 0
    rows = _parse_rows(_decode_csv(CSV_FILE.read_bytes()))
    added, updated, removed, _ = _sync_rows(rows, remove_missing=remove_missing)
    return added, updated, removed


def sync_students_from_upload(
    csv_bytes: bytes,
    remove_missing: bool = True,
    update_fields: Optional[Set[str]] = None,
) -> Tuple[int, int, int, list]:
    """Sync from uploaded CSV bytes. Returns (added, updated, removed, errors)."""
    rows = _parse_rows(_decode_csv(csv_bytes))
    return _sync_rows(rows, remove_missing=remove_missing, update_fields=update_fields)


def preview_students_from_upload(
    csv_bytes: bytes,
    remove_missing: bool,
    update_fields: Set[str],
) -> dict:
    """Dry-run: compute diff without writing to DB."""
    rows = _parse_rows(_decode_csv(csv_bytes))
    return compute_diff(rows, remove_missing=remove_missing, update_fields=update_fields)


def count_students() -> int:
    with Session(ENGINE) as ses:
        return ses.query(Student).count()


if __name__ == "__main__":
    sync_students(remove_missing=False)
