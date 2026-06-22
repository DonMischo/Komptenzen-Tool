"""test_student_loader.py — unit tests for student_loader.py.

Covers:
- CSV parsing helpers (_decode_csv, _parse_date, _parse_rows)
- compute_diff: additions, updates, removals, unchanged, errors
- _sync_rows / sync_students_from_upload: field-level apply logic,
  never-blank-out-existing safety, update_fields gating
- preview_students_from_upload: wires parse + compute_diff
"""
from __future__ import annotations

import io
from datetime import date
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from db_schema import Base, Student, SchoolClass
from student_loader import (
    ALL_UPDATE_FIELDS,
    _decode_csv,
    _parse_date,
    _parse_rows,
    compute_diff,
    preview_students_from_upload,
    sync_students_from_upload,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def loader_engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def seeded_engine(loader_engine):
    """Engine with one class and one student pre-populated."""
    with Session(loader_engine) as ses:
        cls = SchoolClass(name="7a")
        ses.add(cls)
        ses.flush()
        ses.add(Student(
            last_name="Mustermann",
            first_name="Max",
            birthday=date(2012, 5, 15),
            school_class=cls,
            days_absent_excused=2,
            days_absent_unexcused=0,
            lessons_absent_excused=4,
            lessons_absent_unexcused=0,
            report_text="Guter Schüler.",
            remarks="Keine.",
        ))
        ses.commit()
    return loader_engine


def _csv(rows: list[dict], sep: str = ";") -> bytes:
    """Build a UTF-8 CSV from a list of dicts."""
    if not rows:
        return b""
    headers = list(rows[0].keys())
    lines = [sep.join(headers)]
    for r in rows:
        lines.append(sep.join(str(r.get(h, "")) for h in headers))
    return "\n".join(lines).encode("utf-8")


STUDENT_ROW = {
    "Nachname": "Mustermann",
    "Vorname": "Max",
    "Klasse": "7a",
    "Geburtsdatum": "15.05.2012",
    "Fehltage": "2",
    "Fehltage Unentschuldigt": "0",
    "Fehlstunden": "4",
    "Fehlstunden Unentschuldigt": "0",
    "Zeugnistext": "Guter Schüler.",
    "Bemerkungen": "Keine.",
}


# ---------------------------------------------------------------------------
# _decode_csv
# ---------------------------------------------------------------------------

class TestDecodeCsv:
    def test_utf8(self):
        raw = "Nachname;Vorname\nMüller;Hans".encode("utf-8")
        assert "Müller" in _decode_csv(raw)

    def test_utf8_bom(self):
        raw = "Nachname;Vorname\nMüller;Hans".encode("utf-8-sig")
        assert "Müller" in _decode_csv(raw)

    def test_cp1252(self):
        raw = "Nachname;Vorname\nMüller;Hans".encode("cp1252")
        assert "Müller" in _decode_csv(raw)

    def test_latin1(self):
        raw = "Nachname;Vorname\nMüller;Hans".encode("latin-1")
        assert "Müller" in _decode_csv(raw)


# ---------------------------------------------------------------------------
# _parse_date
# ---------------------------------------------------------------------------

class TestParseDate:
    def test_dd_mm_yyyy(self):
        assert _parse_date("15.05.2012") == date(2012, 5, 15)

    def test_yyyy_mm_dd(self):
        assert _parse_date("2012-05-15") == date(2012, 5, 15)

    def test_dd_mm_yy(self):
        assert _parse_date("15.05.12") == date(2012, 5, 15)

    def test_strips_whitespace(self):
        assert _parse_date("  15.05.2012  ") == date(2012, 5, 15)

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            _parse_date("not-a-date")


# ---------------------------------------------------------------------------
# _parse_rows
# ---------------------------------------------------------------------------

class TestParseRows:
    def test_semicolon_delimiter(self):
        csv_text = "Nachname;Vorname;Klasse;Geburtsdatum\nMuster;Anna;6b;01.01.2013"
        rows = _parse_rows(csv_text)
        assert len(rows) == 1
        assert rows[0]["Nachname"] == "Muster"

    def test_comma_delimiter(self):
        csv_text = "Nachname,Vorname,Klasse,Geburtsdatum\nMuster,Anna,6b,01.01.2013"
        rows = _parse_rows(csv_text)
        assert len(rows) == 1

    def test_skips_empty_nachname(self):
        csv_text = "Nachname;Vorname\n;Anna\nMuster;Karl"
        rows = _parse_rows(csv_text)
        assert len(rows) == 1
        assert rows[0]["Nachname"] == "Muster"

    def test_multiple_rows(self):
        csv_text = (
            "Nachname;Vorname;Klasse;Geburtsdatum\n"
            "Alpha;Anna;5a;01.01.2014\n"
            "Beta;Bob;5b;02.02.2014"
        )
        rows = _parse_rows(csv_text)
        assert len(rows) == 2


# ---------------------------------------------------------------------------
# compute_diff — helper: run against loader_engine
# ---------------------------------------------------------------------------

def _diff(loader_engine, rows: list[dict], remove_missing=False,
          update_fields=None):
    if update_fields is None:
        update_fields = ALL_UPDATE_FIELDS
    with patch("student_loader.ENGINE", loader_engine):
        return compute_diff(rows, remove_missing=remove_missing,
                            update_fields=update_fields)


class TestComputeDiffAdditions:
    def test_new_student_in_to_add(self, loader_engine):
        rows = [STUDENT_ROW]
        diff = _diff(loader_engine, rows)
        assert len(diff["to_add"]) == 1
        assert diff["to_add"][0]["name"] == "Max Mustermann"

    def test_no_updates_no_removals_for_new(self, loader_engine):
        rows = [STUDENT_ROW]
        diff = _diff(loader_engine, rows)
        assert diff["to_update"] == []
        assert diff["to_remove"] == []

    def test_unchanged_zero_for_new(self, loader_engine):
        rows = [STUDENT_ROW]
        diff = _diff(loader_engine, rows)
        assert diff["unchanged"] == 0


class TestComputeDiffUnchanged:
    def test_identical_row_is_unchanged(self, seeded_engine):
        rows = [STUDENT_ROW]
        diff = _diff(seeded_engine, rows)
        assert diff["unchanged"] == 1
        assert diff["to_update"] == []
        assert diff["to_add"] == []

    def test_unchanged_not_in_remove(self, seeded_engine):
        rows = [STUDENT_ROW]
        diff = _diff(seeded_engine, rows, remove_missing=False)
        assert diff["to_remove"] == []


class TestComputeDiffUpdates:
    def test_class_change_detected(self, seeded_engine):
        row = {**STUDENT_ROW, "Klasse": "7b"}
        diff = _diff(seeded_engine, [row], update_fields={"klasse"})
        assert len(diff["to_update"]) == 1
        fields = [c["field"] for c in diff["to_update"][0]["changes"]]
        assert "Klasse" in fields

    def test_class_change_shows_old_and_new(self, seeded_engine):
        row = {**STUDENT_ROW, "Klasse": "7b"}
        diff = _diff(seeded_engine, [row], update_fields={"klasse"})
        change = next(c for c in diff["to_update"][0]["changes"] if c["field"] == "Klasse")
        assert change["old"] == "7a"
        assert change["new"] == "7b"

    def test_fehltage_change_detected(self, seeded_engine):
        row = {**STUDENT_ROW, "Fehltage": "5"}
        diff = _diff(seeded_engine, [row], update_fields={"fehltage"})
        assert len(diff["to_update"]) == 1
        fields = [c["field"] for c in diff["to_update"][0]["changes"]]
        assert "Fehlzeiten" in fields

    def test_zeugnistext_change_detected(self, seeded_engine):
        row = {**STUDENT_ROW, "Zeugnistext": "Sehr guter Schüler."}
        diff = _diff(seeded_engine, [row], update_fields={"zeugnistext"})
        assert len(diff["to_update"]) == 1

    def test_field_not_in_update_fields_ignored(self, seeded_engine):
        row = {**STUDENT_ROW, "Klasse": "7b", "Zeugnistext": "Neuer Text"}
        # only fehltage enabled → class and text changes not detected
        diff = _diff(seeded_engine, [row], update_fields={"fehltage"})
        assert diff["to_update"] == []
        assert diff["unchanged"] == 1

    def test_empty_zeugnistext_not_flagged_as_change(self, seeded_engine):
        row = {**STUDENT_ROW, "Zeugnistext": ""}
        diff = _diff(seeded_engine, [row], update_fields={"zeugnistext"})
        # empty new value vs existing non-empty → IS a change (user chose zeugnistext field)
        # this shows the diff but apply won't blank it out
        changes = diff["to_update"][0]["changes"] if diff["to_update"] else []
        text_changes = [c for c in changes if c["field"] == "Zeugnistext"]
        assert len(text_changes) == 1
        assert text_changes[0]["new"] == ""


class TestComputeDiffRemovals:
    def test_missing_student_in_to_remove(self, seeded_engine):
        diff = _diff(seeded_engine, [], remove_missing=True)
        assert len(diff["to_remove"]) == 1

    def test_missing_student_not_removed_when_flag_false(self, seeded_engine):
        diff = _diff(seeded_engine, [], remove_missing=False)
        assert diff["to_remove"] == []


class TestComputeDiffErrors:
    def test_invalid_date_goes_to_errors(self, loader_engine):
        row = {**STUDENT_ROW, "Geburtsdatum": "not-a-date"}
        diff = _diff(loader_engine, [row])
        assert len(diff["errors"]) == 1
        assert "Geburtsdatum" in diff["errors"][0] or "ungültiges" in diff["errors"][0].lower()

    def test_missing_date_key_goes_to_errors(self, loader_engine):
        row = {k: v for k, v in STUDENT_ROW.items() if k != "Geburtsdatum"}
        diff = _diff(loader_engine, [row])
        assert len(diff["errors"]) == 1


# ---------------------------------------------------------------------------
# sync_students_from_upload — apply logic
# ---------------------------------------------------------------------------

def _upload(loader_engine, csv_bytes: bytes, remove_missing=False,
            update_fields=None):
    with patch("student_loader.ENGINE", loader_engine):
        return sync_students_from_upload(
            csv_bytes,
            remove_missing=remove_missing,
            update_fields=update_fields,
        )


class TestSyncAddNew:
    def test_new_student_created(self, loader_engine):
        added, updated, removed, errors = _upload(loader_engine, _csv([STUDENT_ROW]))
        assert added == 1
        assert updated == 0
        assert errors == []
        with Session(loader_engine) as ses:
            stu = ses.query(Student).first()
        assert stu is not None
        assert stu.last_name == "Mustermann"

    def test_new_student_gets_class(self, loader_engine):
        _upload(loader_engine, _csv([STUDENT_ROW]))
        with Session(loader_engine) as ses:
            stu = ses.query(Student).first()
            assert stu.school_class.name == "7a"


class TestSyncIdempotent:
    def test_reimport_same_csv_no_duplicates(self, seeded_engine):
        _upload(seeded_engine, _csv([STUDENT_ROW]))
        _upload(seeded_engine, _csv([STUDENT_ROW]))
        with Session(seeded_engine) as ses:
            count = ses.query(Student).count()
        assert count == 1


class TestSyncUpdateFields:
    def test_klasse_updated_when_in_fields(self, seeded_engine):
        row = {**STUDENT_ROW, "Klasse": "7b"}
        _upload(seeded_engine, _csv([row]), update_fields={"klasse"})
        with Session(seeded_engine) as ses:
            stu = ses.query(Student).first()
            assert stu.school_class.name == "7b"

    def test_klasse_not_updated_when_not_in_fields(self, seeded_engine):
        row = {**STUDENT_ROW, "Klasse": "7b"}
        _upload(seeded_engine, _csv([row]), update_fields=set())
        with Session(seeded_engine) as ses:
            stu = ses.query(Student).first()
            assert stu.school_class.name == "7a"

    def test_fehltage_updated_when_in_fields(self, seeded_engine):
        row = {**STUDENT_ROW, "Fehltage": "10"}
        _upload(seeded_engine, _csv([row]), update_fields={"fehltage"})
        with Session(seeded_engine) as ses:
            stu = ses.query(Student).first()
            assert stu.days_absent_excused == 10

    def test_fehltage_not_updated_when_not_in_fields(self, seeded_engine):
        row = {**STUDENT_ROW, "Fehltage": "10"}
        _upload(seeded_engine, _csv([row]), update_fields=set())
        with Session(seeded_engine) as ses:
            stu = ses.query(Student).first()
            assert stu.days_absent_excused == 2  # original value

    def test_zeugnistext_updated_when_in_fields_and_nonempty(self, seeded_engine):
        row = {**STUDENT_ROW, "Zeugnistext": "Neuer Text"}
        _upload(seeded_engine, _csv([row]), update_fields={"zeugnistext"})
        with Session(seeded_engine) as ses:
            stu = ses.query(Student).first()
            assert stu.report_text == "Neuer Text"

    def test_zeugnistext_not_blanked_when_csv_empty(self, seeded_engine):
        row = {**STUDENT_ROW, "Zeugnistext": ""}
        _upload(seeded_engine, _csv([row]), update_fields={"zeugnistext"})
        with Session(seeded_engine) as ses:
            stu = ses.query(Student).first()
            assert stu.report_text == "Guter Schüler."  # untouched

    def test_bemerkungen_not_blanked_when_csv_empty(self, seeded_engine):
        row = {**STUDENT_ROW, "Bemerkungen": ""}
        _upload(seeded_engine, _csv([row]), update_fields={"bemerkungen"})
        with Session(seeded_engine) as ses:
            stu = ses.query(Student).first()
            assert stu.remarks == "Keine."  # untouched

    def test_zeugnistext_not_updated_when_not_in_fields(self, seeded_engine):
        row = {**STUDENT_ROW, "Zeugnistext": "Neuer Text"}
        _upload(seeded_engine, _csv([row]), update_fields=set())
        with Session(seeded_engine) as ses:
            stu = ses.query(Student).first()
            assert stu.report_text == "Guter Schüler."

    def test_bemerkungen_updated_when_in_fields(self, seeded_engine):
        row = {**STUDENT_ROW, "Bemerkungen": "Neue Bemerkung"}
        _upload(seeded_engine, _csv([row]), update_fields={"bemerkungen"})
        with Session(seeded_engine) as ses:
            stu = ses.query(Student).first()
            assert stu.remarks == "Neue Bemerkung"


class TestSyncRemoveMissing:
    def test_remove_missing_true_deletes_student(self, seeded_engine):
        _upload(seeded_engine, _csv([]), remove_missing=True)
        with Session(seeded_engine) as ses:
            assert ses.query(Student).count() == 0

    def test_remove_missing_false_keeps_student(self, seeded_engine):
        _upload(seeded_engine, _csv([]), remove_missing=False)
        with Session(seeded_engine) as ses:
            assert ses.query(Student).count() == 1

    def test_remove_count_returned(self, seeded_engine):
        _, _, removed, _ = _upload(seeded_engine, _csv([]), remove_missing=True)
        assert removed == 1


class TestSyncErrors:
    def test_invalid_date_skipped_with_error(self, loader_engine):
        row = {**STUDENT_ROW, "Geburtsdatum": "bad"}
        added, updated, removed, errors = _upload(loader_engine, _csv([row]))
        assert added == 0
        assert len(errors) == 1

    def test_valid_rows_still_imported_despite_error(self, loader_engine):
        good = STUDENT_ROW
        bad = {**STUDENT_ROW, "Nachname": "Fehler", "Geburtsdatum": "bad"}
        added, _, _, errors = _upload(loader_engine, _csv([good, bad]))
        assert added == 1
        assert len(errors) == 1


# ---------------------------------------------------------------------------
# preview_students_from_upload
# ---------------------------------------------------------------------------

class TestPreviewStudentsFromUpload:
    def test_returns_diff_structure(self, loader_engine):
        with patch("student_loader.ENGINE", loader_engine):
            result = preview_students_from_upload(
                _csv([STUDENT_ROW]), False, ALL_UPDATE_FIELDS
            )
        assert "to_add" in result
        assert "to_update" in result
        assert "to_remove" in result
        assert "unchanged" in result
        assert "errors" in result

    def test_does_not_write_to_db(self, loader_engine):
        with patch("student_loader.ENGINE", loader_engine):
            preview_students_from_upload(_csv([STUDENT_ROW]), False, ALL_UPDATE_FIELDS)
        with Session(loader_engine) as ses:
            assert ses.query(Student).count() == 0

    def test_new_student_appears_in_to_add(self, loader_engine):
        with patch("student_loader.ENGINE", loader_engine):
            result = preview_students_from_upload(
                _csv([STUDENT_ROW]), False, ALL_UPDATE_FIELDS
            )
        assert len(result["to_add"]) == 1

    def test_existing_unchanged_student_in_unchanged(self, seeded_engine):
        with patch("student_loader.ENGINE", seeded_engine):
            result = preview_students_from_upload(
                _csv([STUDENT_ROW]), False, ALL_UPDATE_FIELDS
            )
        assert result["unchanged"] == 1
        assert result["to_update"] == []
