"""test_api_students.py — API tests for the student import endpoints.

Tests POST /api/setup/students/preview and POST /api/setup/students/upload,
using the client fixture (SQLite + auth override from conftest).
The student_loader functions are mocked so these tests only verify the
HTTP layer: field parsing, response shape, and error handling.
"""
from __future__ import annotations

import io
from unittest.mock import patch

import pytest


def _csv_file(content: str = "Nachname;Vorname\nMuster;Anna") -> tuple:
    return ("file", ("students.csv", content.encode("utf-8"), "text/csv"))


PREVIEW_RESULT = {
    "to_add": [{"name": "Anna Muster", "school_class": "6a", "action": "add", "changes": []}],
    "to_update": [],
    "to_remove": [],
    "unchanged": 0,
    "errors": [],
}

UPLOAD_RESULT = (1, 0, 0, [])


# ---------------------------------------------------------------------------
# POST /api/setup/students/preview
# ---------------------------------------------------------------------------

class TestStudentPreviewEndpoint:
    def test_returns_200(self, client):
        with patch("routers.setup.preview_students_from_upload", return_value=PREVIEW_RESULT):
            r = client.post(
                "/api/setup/students/preview",
                files=[_csv_file()],
                data={"remove_missing": "false", "update_fields": "klasse,fehltage"},
            )
        assert r.status_code == 200

    def test_response_has_required_keys(self, client):
        with patch("routers.setup.preview_students_from_upload", return_value=PREVIEW_RESULT):
            r = client.post(
                "/api/setup/students/preview",
                files=[_csv_file()],
                data={"remove_missing": "false", "update_fields": "klasse,fehltage"},
            )
        data = r.json()
        assert "to_add" in data
        assert "to_update" in data
        assert "to_remove" in data
        assert "unchanged" in data
        assert "errors" in data

    def test_to_add_content(self, client):
        with patch("routers.setup.preview_students_from_upload", return_value=PREVIEW_RESULT):
            r = client.post(
                "/api/setup/students/preview",
                files=[_csv_file()],
                data={"remove_missing": "false", "update_fields": "klasse,fehltage"},
            )
        assert r.json()["to_add"][0]["name"] == "Anna Muster"

    def test_update_fields_parsed_as_set(self, client):
        captured = {}

        def fake_preview(csv_bytes, remove_missing, update_fields):
            captured["fields"] = update_fields
            return PREVIEW_RESULT

        with patch("routers.setup.preview_students_from_upload", side_effect=fake_preview):
            client.post(
                "/api/setup/students/preview",
                files=[_csv_file()],
                data={"remove_missing": "false", "update_fields": "klasse,zeugnistext"},
            )
        assert "klasse" in captured["fields"]
        assert "zeugnistext" in captured["fields"]
        assert "fehltage" not in captured["fields"]

    def test_remove_missing_passed_correctly(self, client):
        captured = {}

        def fake_preview(csv_bytes, remove_missing, update_fields):
            captured["remove_missing"] = remove_missing
            return PREVIEW_RESULT

        with patch("routers.setup.preview_students_from_upload", side_effect=fake_preview):
            client.post(
                "/api/setup/students/preview",
                files=[_csv_file()],
                data={"remove_missing": "true", "update_fields": "klasse"},
            )
        assert captured["remove_missing"] is True

    def test_exception_returns_400(self, client):
        with patch(
            "routers.setup.preview_students_from_upload",
            side_effect=ValueError("Bad CSV"),
        ):
            r = client.post(
                "/api/setup/students/preview",
                files=[_csv_file("garbage")],
                data={"remove_missing": "false", "update_fields": "klasse"},
            )
        assert r.status_code == 400

    def test_default_update_fields_used_when_not_provided(self, client):
        captured = {}

        def fake_preview(csv_bytes, remove_missing, update_fields):
            captured["fields"] = update_fields
            return PREVIEW_RESULT

        with patch("routers.setup.preview_students_from_upload", side_effect=fake_preview):
            client.post(
                "/api/setup/students/preview",
                files=[_csv_file()],
                data={"remove_missing": "false"},
            )
        # default is "klasse,fehltage,zeugnistext,bemerkungen"
        assert len(captured.get("fields", set())) > 0


# ---------------------------------------------------------------------------
# POST /api/setup/students/upload
# ---------------------------------------------------------------------------

class TestStudentUploadEndpoint:
    def test_returns_200(self, client):
        with patch("routers.setup.sync_students_from_upload", return_value=UPLOAD_RESULT):
            r = client.post(
                "/api/setup/students/upload",
                files=[_csv_file()],
                data={"remove_missing": "false", "update_fields": "klasse,fehltage"},
            )
        assert r.status_code == 200

    def test_response_shape(self, client):
        with patch("routers.setup.sync_students_from_upload", return_value=UPLOAD_RESULT):
            r = client.post(
                "/api/setup/students/upload",
                files=[_csv_file()],
                data={"remove_missing": "false", "update_fields": "klasse"},
            )
        data = r.json()
        assert "added" in data
        assert "updated" in data
        assert "removed" in data
        assert "errors" in data

    def test_counts_match_backend_result(self, client):
        with patch("routers.setup.sync_students_from_upload", return_value=(3, 1, 2, [])):
            r = client.post(
                "/api/setup/students/upload",
                files=[_csv_file()],
                data={"remove_missing": "false", "update_fields": "klasse"},
            )
        data = r.json()
        assert data["added"] == 3
        assert data["updated"] == 1
        assert data["removed"] == 2

    def test_update_fields_passed_to_loader(self, client):
        captured = {}

        def fake_upload(csv_bytes, remove_missing, update_fields):
            captured["fields"] = update_fields
            return UPLOAD_RESULT

        with patch("routers.setup.sync_students_from_upload", side_effect=fake_upload):
            client.post(
                "/api/setup/students/upload",
                files=[_csv_file()],
                data={"remove_missing": "false", "update_fields": "fehltage,bemerkungen"},
            )
        assert "fehltage" in captured["fields"]
        assert "bemerkungen" in captured["fields"]
        assert "zeugnistext" not in captured["fields"]

    def test_default_update_fields_conservative(self, client):
        """Default should NOT include zeugnistext or bemerkungen."""
        captured = {}

        def fake_upload(csv_bytes, remove_missing, update_fields):
            captured["fields"] = update_fields
            return UPLOAD_RESULT

        with patch("routers.setup.sync_students_from_upload", side_effect=fake_upload):
            client.post(
                "/api/setup/students/upload",
                files=[_csv_file()],
                data={"remove_missing": "false"},
            )
        assert "zeugnistext" not in captured.get("fields", set())
        assert "bemerkungen" not in captured.get("fields", set())

    def test_errors_returned_in_response(self, client):
        with patch(
            "routers.setup.sync_students_from_upload",
            return_value=(0, 0, 0, ["Anna: ungültiges Geburtsdatum"]),
        ):
            r = client.post(
                "/api/setup/students/upload",
                files=[_csv_file()],
                data={"remove_missing": "false", "update_fields": "klasse"},
            )
        assert r.json()["errors"] == ["Anna: ungültiges Geburtsdatum"]

    def test_exception_returns_400(self, client):
        with patch(
            "routers.setup.sync_students_from_upload",
            side_effect=ValueError("Parse error"),
        ):
            r = client.post(
                "/api/setup/students/upload",
                files=[_csv_file("garbage")],
                data={"remove_missing": "false", "update_fields": "klasse"},
            )
        assert r.status_code == 400
