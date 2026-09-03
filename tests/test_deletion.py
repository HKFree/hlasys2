"""
Integration tests for soft deletion, against a real SQLite database built from
schema.sql. These cover the parts that pure unit tests cannot: the
`event.created = proposal.deleted` coupling, the TOCTOU guard, and the
server-side blocks that keep a deleted proposal read-only.
"""
import json
import sqlite3

import pytest

DECIDERS = {"277": "Jakub", "797": "zitnyp", "1980": "pavkriz"}
AUTHOR = 9000
DECIDER = 277
STRANGER = 5555


@pytest.fixture
def app(tmp_path, monkeypatch):
    import hlasys2_app
    from hlasys2_app import create_app, decorators
    from hlasys2_app.db import init_db

    # Outside development, create_app wires up OIDC (demanding
    # client_secrets.json) and login_required defers to it. Both modules bind
    # HLASYS_ENV at import time, so patch both and stop depending on whatever
    # config.py happens to say.
    monkeypatch.setattr(hlasys2_app, "HLASYS_ENV", "development")
    monkeypatch.setattr(decorators, "HLASYS_ENV", "development")
    monkeypatch.setattr(
        decorators, "DEV_USERS", [{"id": AUTHOR, "family_name": f"User{AUTHOR}"}]
    )

    application = create_app()
    application.config.update(
        DATABASE=str(tmp_path / "test.sqlite"),
        WTF_CSRF_ENABLED=False,
        TESTING=True,
    )
    with application.app_context():
        init_db()
    return application


@pytest.fixture
def db_path(app):
    return app.config["DATABASE"]


def raw(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def add_proposal(db_path, **overrides):
    """Insert a live, undecided VV proposal authored by AUTHOR. Returns its id."""
    row = {
        "author_id": AUTHOR,
        "author_name": "Autor",
        "type": 0,
        "subject": "Testovací návrh",
        "description": "Popis",
        "cost": 1000,
        "deciders": json.dumps(DECIDERS, ensure_ascii=False),
        "acceptance_treshold": 2,
    }
    # decided/deleted are not part of the INSERT; apply them afterwards.
    decided = overrides.pop("decided", None)
    deleted = overrides.pop("deleted", None)
    row.update(overrides)
    conn = raw(db_path)
    cur = conn.execute(
        """INSERT INTO proposal
               (author_id, author_name, type, subject, description, cost,
                deciders, acceptance_treshold)
           VALUES (:author_id, :author_name, :type, :subject, :description,
                   :cost, :deciders, :acceptance_treshold)""",
        row,
    )
    pid = cur.lastrowid
    if decided is not None:
        conn.execute("UPDATE proposal SET decided = ? WHERE id = ?", (decided, pid))
    if deleted is not None:
        conn.execute("UPDATE proposal SET deleted = ? WHERE id = ?", (deleted, pid))
    conn.commit()
    conn.close()
    return pid


def login(client, user_id):
    with client.session_transaction() as sess:
        sess["oidc_auth_profile"] = {
            "preferred_username": str(user_id),
            "family_name": f"User{user_id}",
        }


def event_count(db_path, pid):
    conn = raw(db_path)
    n = conn.execute(
        "SELECT COUNT(*) FROM event WHERE proposal_id = ?", (pid,)
    ).fetchone()[0]
    conn.close()
    return n


def delete_as(client, pid, user_id, reason=""):
    login(client, user_id)
    return client.post(f"/proposal/{pid}/delete", data={"reason": reason})


# --------------------------------------------------------------------------
# The deletion write itself
# --------------------------------------------------------------------------

def test_delete_sets_timestamp_and_logs_one_event(app, db_path):
    pid = add_proposal(db_path)
    with app.test_client() as client:
        assert delete_as(client, pid, AUTHOR, "Duplicita").status_code == 302

    conn = raw(db_path)
    proposal = conn.execute(
        "SELECT deleted, decided FROM proposal WHERE id = ?", (pid,)
    ).fetchone()
    assert proposal["deleted"] is not None
    assert proposal["decided"] is None
    assert event_count(db_path, pid) == 1

    event = conn.execute(
        "SELECT * FROM event WHERE proposal_id = ?", (pid,)
    ).fetchone()
    assert event["author_id"] == AUTHOR
    assert event["decision"] is None
    assert "Duplicita" in event["comment"]
    conn.close()


def test_deleter_is_recoverable_by_the_timestamp_join(app, db_path):
    """The whole audit trail hangs on event.created == proposal.deleted."""
    pid = add_proposal(db_path)
    with app.test_client() as client:
        delete_as(client, pid, AUTHOR)

    conn = raw(db_path)
    found = conn.execute(
        """SELECT e.author_id, e.author_name
           FROM event e
           JOIN proposal p ON p.id = e.proposal_id AND e.created = p.deleted
           WHERE p.id = ?""",
        (pid,),
    ).fetchone()
    conn.close()
    assert found is not None
    assert found["author_id"] == AUTHOR


def test_legacy_row_without_an_event_yields_no_deleter(app, db_path):
    """The 237 rows hidden during the 2005 migration must render as unknown."""
    pid = add_proposal(db_path)
    conn = raw(db_path)
    conn.execute(
        "UPDATE proposal SET deleted = '2026-01-28 21:29:00.459654' WHERE id = ?",
        (pid,),
    )
    conn.commit()
    found = conn.execute(
        """SELECT e.author_name
           FROM event e
           JOIN proposal p ON p.id = e.proposal_id AND e.created = p.deleted
           WHERE p.id = ?""",
        (pid,),
    ).fetchone()
    conn.close()
    assert found is None


def test_double_submit_produces_no_second_event(app, db_path):
    pid = add_proposal(db_path)
    with app.test_client() as client:
        delete_as(client, pid, AUTHOR)
        assert event_count(db_path, pid) == 1
        delete_as(client, pid, AUTHOR, "znovu")
    assert event_count(db_path, pid) == 1


def test_decided_proposal_cannot_be_deleted(app, db_path):
    pid = add_proposal(db_path, decided="2026-01-01 00:00:00")
    with app.test_client() as client:
        delete_as(client, pid, AUTHOR)
    conn = raw(db_path)
    assert conn.execute(
        "SELECT deleted FROM proposal WHERE id = ?", (pid,)
    ).fetchone()["deleted"] is None
    conn.close()


def test_stranger_cannot_delete(app, db_path):
    pid = add_proposal(db_path)
    with app.test_client() as client:
        delete_as(client, pid, STRANGER)
    conn = raw(db_path)
    assert conn.execute(
        "SELECT deleted FROM proposal WHERE id = ?", (pid,)
    ).fetchone()["deleted"] is None
    conn.close()


def test_decider_on_a_small_committee_can_delete(app, db_path):
    pid = add_proposal(db_path)
    with app.test_client() as client:
        delete_as(client, pid, DECIDER)
    conn = raw(db_path)
    assert conn.execute(
        "SELECT deleted FROM proposal WHERE id = ?", (pid,)
    ).fetchone()["deleted"] is not None
    conn.close()


def test_invalid_post_tells_the_user_something_went_wrong(app, db_path):
    """A rejected form must not silently re-render an unchanged page."""
    pid = add_proposal(db_path)
    app.config["WTF_CSRF_ENABLED"] = True
    with app.test_client() as client:
        login(client, AUTHOR)
        response = client.post(f"/proposal/{pid}/delete", data={"reason": "x"})
        assert response.status_code == 302
        with client.session_transaction() as sess:
            flashes = [message for _, message in sess.get("_flashes", [])]
    assert flashes, "expected a flash explaining the rejection"
    assert event_count(db_path, pid) == 0


# --------------------------------------------------------------------------
# A deleted proposal must be inert
# --------------------------------------------------------------------------

def test_commenting_on_a_deleted_proposal_is_blocked(app, db_path):
    pid = add_proposal(db_path)
    with app.test_client() as client:
        delete_as(client, pid, AUTHOR)
        before = event_count(db_path, pid)

        login(client, STRANGER)
        response = client.post(
            f"/proposal/{pid}/comment", data={"comment": "nemělo by projít"}
        )
        assert response.status_code == 302
    assert event_count(db_path, pid) == before


def test_changing_state_of_a_deleted_proposal_is_blocked(app, db_path):
    from hlasys2_app import config

    pid = add_proposal(db_path)
    with app.test_client() as client:
        delete_as(client, pid, AUTHOR)
        before = event_count(db_path, pid)

        login(client, config.USERS_CHANGE_STATE[0])
        response = client.get(f"/proposal/{pid}/state/Objednáno")
        assert response.status_code == 302

    conn = raw(db_path)
    assert conn.execute(
        "SELECT state FROM proposal WHERE id = ?", (pid,)
    ).fetchone()["state"] is None
    conn.close()
    assert event_count(db_path, pid) == before


def test_voting_on_a_deleted_proposal_is_blocked(app, db_path):
    pid = add_proposal(db_path)
    with app.test_client() as client:
        delete_as(client, pid, AUTHOR)
        login(client, DECIDER)
        response = client.post(f"/proposal/{pid}/quick-vote", data={"decision": "for"})
        assert response.status_code == 302

    conn = raw(db_path)
    votes = conn.execute(
        "SELECT COUNT(*) FROM event WHERE proposal_id = ? AND decision IS NOT NULL",
        (pid,),
    ).fetchone()[0]
    conn.close()
    assert votes == 0


def test_deleted_proposal_renders_read_only(app, db_path):
    pid = add_proposal(db_path)
    with app.test_client() as client:
        delete_as(client, pid, AUTHOR, "Duplicita")
        login(client, DECIDER)
        body = client.get(f"/proposal/{pid}").get_data(as_text=True)

    assert "d-deleted-banner" in body
    assert "Duplicita" in body
    assert "Hlasovat PRO" not in body
    assert "Přidat komentář" not in body
    assert "Smazat návrh" not in body


# --------------------------------------------------------------------------
# Listing
# --------------------------------------------------------------------------

def test_kos_lists_deleted_and_overview_does_not(app, db_path):
    live = add_proposal(db_path, subject="Zivy navrh")
    gone = add_proposal(db_path, subject="Smazany navrh")
    with app.test_client() as client:
        delete_as(client, gone, AUTHOR)

        login(client, AUTHOR)
        overview = client.get("/overview/vv").get_data(as_text=True)
        kos = client.get("/overview/vv?deleted=1").get_data(as_text=True)

    assert f'/proposal/{live}"' in overview
    assert f'/proposal/{gone}"' not in overview
    assert f'/proposal/{gone}"' in kos
    assert f'/proposal/{live}"' not in kos
    assert f"User{AUTHOR}" in kos


def test_timeline_excludes_deleted_proposals(app, db_path):
    live = add_proposal(db_path, subject="Zivy navrh")
    gone = add_proposal(db_path, subject="Smazany navrh")
    with app.test_client() as client:
        delete_as(client, gone, AUTHOR)
        login(client, AUTHOR)
        body = client.get(f"/user/{AUTHOR}").get_data(as_text=True)

    assert f'/proposal/{live}"' in body
    assert f'/proposal/{gone}"' not in body
