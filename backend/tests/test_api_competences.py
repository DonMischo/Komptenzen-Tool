"""test_api_competences.py — HTTP-layer tests for routers/competences.py.

Endpoint-level tests; DB functions are tested in test_db_helpers.py.
Uses the shared sqlite_engine from conftest for endpoints that need real data,
and mocks for endpoints that just proxy to db_helpers.
"""
from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from db_schema import Base, SchoolClass, Subject, Topic, Competence, Student


# ---------------------------------------------------------------------------
# Seed fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def comp_seed(client, sqlite_engine):
    """Seed subject Mathematik with one topic and two competences, plus class 9a."""
    Base.metadata.create_all(sqlite_engine)
    with Session(sqlite_engine) as ses:
        cls = SchoolClass(name="9a")
        ses.add(cls)
        ses.flush()
        subj = Subject(name="Mathematik_c")   # unique name to avoid conflicts
        ses.add(subj)
        ses.flush()
        t1 = Topic(name="Zahlen_c", block="5/6", subject=subj)
        ses.add(t1)
        ses.flush()
        c1 = Competence(text="Kann zählen", topic=t1)
        c2 = Competence(text="Kann addieren", topic=t1)
        ses.add_all([c1, c2])
        ses.commit()
        ids = {"cls_id": cls.id, "subj_id": subj.id, "t1_id": t1.id,
               "c1_id": c1.id, "c2_id": c2.id,
               "subj_name": "Mathematik_c", "topic_block": "5/6"}
    yield ids
    with Session(sqlite_engine) as ses:
        ses.query(Competence).filter(Competence.topic_id == ids["t1_id"]).delete()
        ses.query(Topic).filter_by(id=ids["t1_id"]).delete()
        ses.query(Subject).filter_by(id=ids["subj_id"]).delete()
        ses.query(SchoolClass).filter_by(id=ids["cls_id"]).delete()
        ses.commit()


# ---------------------------------------------------------------------------
# GET /api/classes
# ---------------------------------------------------------------------------

class TestListClasses:
    def test_returns_200(self, client):
        r = client.get("/api/classes")
        assert r.status_code == 200

    def test_response_has_classes_key(self, client):
        r = client.get("/api/classes")
        assert "classes" in r.json()

    def test_returns_list(self, client, comp_seed):
        r = client.get("/api/classes")
        assert isinstance(r.json()["classes"], list)


# ---------------------------------------------------------------------------
# GET /api/subjects
# ---------------------------------------------------------------------------

class TestListSubjects:
    def test_returns_200(self, client):
        with patch("routers.competences.get_subjects", return_value=["Mathematik", "Deutsch"]):
            r = client.get("/api/subjects")
        assert r.status_code == 200

    def test_response_has_subjects_key(self, client):
        with patch("routers.competences.get_subjects", return_value=["Mathematik"]):
            r = client.get("/api/subjects")
        assert "subjects" in r.json()

    def test_returns_correct_list(self, client):
        with patch("routers.competences.get_subjects", return_value=["Deutsch", "Mathematik"]):
            r = client.get("/api/subjects")
        assert r.json()["subjects"] == ["Deutsch", "Mathematik"]


# ---------------------------------------------------------------------------
# GET /api/subjects/{name}/blocks
# ---------------------------------------------------------------------------

class TestListBlocks:
    def test_returns_200(self, client):
        with patch("routers.competences.get_blocks", return_value=["5/6", "7/8"]):
            r = client.get("/api/subjects/Mathematik/blocks")
        assert r.status_code == 200

    def test_response_has_blocks_key(self, client):
        with patch("routers.competences.get_blocks", return_value=["5/6"]):
            r = client.get("/api/subjects/Mathematik/blocks")
        assert "blocks" in r.json()

    def test_empty_for_unknown_subject(self, client):
        with patch("routers.competences.get_blocks", return_value=[]):
            r = client.get("/api/subjects/Nichtexistent/blocks")
        assert r.json()["blocks"] == []


# ---------------------------------------------------------------------------
# GET /api/competences
# ---------------------------------------------------------------------------

_FAKE_ROWS = [
    (1, "Zahlen_c", "Kann zählen", False),
    (2, "Zahlen_c", "Kann addieren", False),
]


class TestListCompetences:
    def test_returns_200(self, client, comp_seed):
        with (
            patch("routers.competences.load_topic_rows", return_value=_FAKE_ROWS),
            patch("routers.competences._get_or_create_class_id", return_value=comp_seed["cls_id"]),
            patch("routers.competences.get_custom_competences", return_value=[]),
        ):
            r = client.get("/api/competences", params={
                "class_name": "9a",
                "subject": "Mathematik_c",
                "block": "5/6",
            })
        assert r.status_code == 200

    def test_response_shape(self, client, comp_seed):
        with (
            patch("routers.competences.load_topic_rows", return_value=_FAKE_ROWS),
            patch("routers.competences._get_or_create_class_id", return_value=comp_seed["cls_id"]),
            patch("routers.competences.get_custom_competences", return_value=[]),
        ):
            r = client.get("/api/competences", params={
                "class_name": "9a",
                "subject": "Mathematik_c",
                "block": "5/6",
            })
        data = r.json()
        assert "class_name" in data
        assert "subject" in data
        assert "block" in data
        assert "topics" in data

    def test_contains_competences(self, client, comp_seed):
        with (
            patch("routers.competences.load_topic_rows", return_value=_FAKE_ROWS),
            patch("routers.competences._get_or_create_class_id", return_value=comp_seed["cls_id"]),
            patch("routers.competences.get_custom_competences", return_value=[]),
        ):
            r = client.get("/api/competences", params={
                "class_name": "9a",
                "subject": "Mathematik_c",
                "block": "5/6",
            })
        topics = r.json()["topics"]
        all_texts = [c["text"] for t in topics for c in t["competences"]]
        assert "Kann zählen" in all_texts
        assert "Kann addieren" in all_texts


# ---------------------------------------------------------------------------
# POST /api/competences/save
# ---------------------------------------------------------------------------

class TestSaveCompetences:
    def test_returns_200(self, client):
        with patch("routers.competences.save_selections"):
            r = client.post("/api/competences/save", json={
                "class_name": "9a",
                "changes": [[1, True], [2, False]],
            })
        assert r.status_code == 200

    def test_returns_ok(self, client):
        with patch("routers.competences.save_selections"):
            r = client.post("/api/competences/save", json={
                "class_name": "9a",
                "changes": [],
            })
        assert r.json()["ok"] is True

    def test_calls_save_selections(self, client):
        with patch("routers.competences.save_selections") as mock_save:
            client.post("/api/competences/save", json={
                "class_name": "9a",
                "changes": [[5, True]],
            })
        mock_save.assert_called_once_with("9a", [(5, True)])


# ---------------------------------------------------------------------------
# POST /api/competences/toggle-topic
# ---------------------------------------------------------------------------

class TestToggleTopic:
    def test_returns_200(self, client):
        with patch("routers.competences.toggle_topic"):
            r = client.post("/api/competences/toggle-topic", json={
                "class_name": "9a", "topic_id": 1, "value": True,
            })
        assert r.status_code == 200

    def test_calls_toggle_topic(self, client):
        with patch("routers.competences.toggle_topic") as mock_toggle:
            client.post("/api/competences/toggle-topic", json={
                "class_name": "9a", "topic_id": 3, "value": False,
            })
        mock_toggle.assert_called_once_with("9a", 3, False)


# ---------------------------------------------------------------------------
# POST /api/competences/custom
# ---------------------------------------------------------------------------

class TestAddCustomCompetence:
    def test_returns_200(self, client, comp_seed):
        r = client.post("/api/competences/custom", json={
            "class_name": "9a",
            "topic_id": comp_seed["t1_id"],
            "text": "Eigene Kompetenz",
        })
        assert r.status_code == 200

    def test_returns_id_and_text(self, client, comp_seed):
        r = client.post("/api/competences/custom", json={
            "class_name": "9a",
            "topic_id": comp_seed["t1_id"],
            "text": "Meine Kompetenz",
        })
        data = r.json()
        assert "id" in data
        assert data["text"] == "Meine Kompetenz"


# ---------------------------------------------------------------------------
# DELETE /api/competences/custom/{comp_id}
# ---------------------------------------------------------------------------

class TestDeleteCustomCompetence:
    def test_delete_existing_returns_200(self, client, comp_seed):
        # First add
        r = client.post("/api/competences/custom", json={
            "class_name": "9a",
            "topic_id": comp_seed["t1_id"],
            "text": "To delete",
        })
        cc_id = r.json()["id"]
        r2 = client.delete(f"/api/competences/custom/{cc_id}")
        assert r2.status_code == 200

    def test_delete_nonexistent_returns_200(self, client):
        # delete_custom_competence is a noop for unknown ids
        r = client.delete("/api/competences/custom/999999")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# POST /api/competences/sync-to-parallel
# ---------------------------------------------------------------------------

class TestSyncToParallel:
    def test_returns_200(self, client):
        with patch("routers.competences.sync_competences_to_parallel", return_value=["9b", "9c"]):
            r = client.post("/api/competences/sync-to-parallel", params={"class_name": "9a"})
        assert r.status_code == 200

    def test_returns_synced_classes(self, client):
        with patch("routers.competences.sync_competences_to_parallel", return_value=["9b", "9c"]):
            r = client.post("/api/competences/sync-to-parallel", params={"class_name": "9a"})
        assert r.json()["synced_to"] == ["9b", "9c"]

    def test_empty_when_no_parallels(self, client):
        with patch("routers.competences.sync_competences_to_parallel", return_value=[]):
            r = client.post("/api/competences/sync-to-parallel", params={"class_name": "9a"})
        assert r.json()["synced_to"] == []

    def test_target_classes_passed_to_helper(self, client):
        """Body {"target_classes": ["9b"]} is forwarded to the helper."""
        with patch("routers.competences.sync_competences_to_parallel", return_value=["9b"]) as mock:
            client.post("/api/competences/sync-to-parallel",
                        params={"class_name": "9a"},
                        json={"target_classes": ["9b"]})
        mock.assert_called_once_with("9a", ["9b"])

    def test_no_body_passes_none_targets(self, client):
        """No JSON body → helper receives None (sync all)."""
        with patch("routers.competences.sync_competences_to_parallel", return_value=["9b"]) as mock:
            client.post("/api/competences/sync-to-parallel", params={"class_name": "9a"})
        mock.assert_called_once_with("9a", None)

    def test_empty_target_list_passes_none(self, client):
        """Empty target_classes list → treated as None (sync all)."""
        with patch("routers.competences.sync_competences_to_parallel", return_value=[]) as mock:
            client.post("/api/competences/sync-to-parallel",
                        params={"class_name": "9a"},
                        json={"target_classes": []})
        mock.assert_called_once_with("9a", None)

    def test_multiple_targets_returned(self, client):
        with patch("routers.competences.sync_competences_to_parallel", return_value=["9b", "9c"]):
            r = client.post("/api/competences/sync-to-parallel",
                            params={"class_name": "9a"},
                            json={"target_classes": ["9b", "9c"]})
        assert set(r.json()["synced_to"]) == {"9b", "9c"}
