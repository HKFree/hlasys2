"""
Stored author names: "<real name> - <nick>" from the SSO profile, plus the
backfill of old rows.
"""
from hlasys2_app.util import display_name
from tests.test_deletion import (  # noqa: F401 - fixtures
    app, db_path, add_proposal, raw, DECIDER, DECIDERS,
)


def test_display_name_combines_real_name_and_nick():
    assert display_name("Ondřej Pithart", "Ondra Lhota") == "Ondřej Pithart - Ondra Lhota"


def test_display_name_falls_back_to_whichever_is_present():
    assert display_name("Ondřej Pithart", None) == "Ondřej Pithart"
    assert display_name("", "Ondra Lhota") == "Ondra Lhota"


def test_display_name_drops_a_nick_that_repeats_the_real_name():
    assert display_name("Jakub", "jakub") == "Jakub"


def test_vote_is_stored_with_real_name_and_nick(app, db_path):
    pid = add_proposal(db_path)
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["oidc_auth_profile"] = {
                "preferred_username": str(DECIDER),
                "family_name": "Jakub Novák",
                "given_name": "Jakub",
            }
        client.post(f"/proposal/{pid}/quick-vote", data={"decision": "for"})

    conn = raw(db_path)
    name = conn.execute(
        "SELECT author_name FROM event WHERE proposal_id = ? AND decision = 1", (pid,)
    ).fetchone()[0]
    conn.close()
    assert name == "Jakub Novák - Jakub"


def add_event(db_path, pid, author_id, author_name):
    conn = raw(db_path)
    conn.execute(
        "INSERT INTO event (proposal_id, author_id, author_name, decision) VALUES (?, ?, ?, 1)",
        (pid, author_id, author_name),
    )
    conn.commit()
    conn.close()


def event_names(db_path):
    conn = raw(db_path)
    names = [r[0] for r in conn.execute("SELECT author_name FROM event ORDER BY id")]
    conn.close()
    return names


def test_backfill_dry_run_changes_nothing(app, db_path):
    from hlasys2_app.db import backfill_names

    pid = add_proposal(db_path)
    add_event(db_path, pid, DECIDER, "Jakub Novák")
    with app.app_context():
        changes = backfill_names(apply=False)

    assert changes == {("event", "Jakub Novák", "Jakub Novák - Jakub"): 1}
    assert event_names(db_path) == ["Jakub Novák"]


def test_backfill_apply_is_idempotent_and_skips_unknown_users(app, db_path):
    from hlasys2_app.db import backfill_names

    pid = add_proposal(db_path)
    add_event(db_path, pid, DECIDER, "Jakub Novák")
    add_event(db_path, pid, 5555, "Někdo Cizí")  # in no deciders snapshot
    with app.app_context():
        backfill_names(apply=True)
        assert backfill_names(apply=False) == {}

    assert event_names(db_path) == ["Jakub Novák - Jakub", "Někdo Cizí"]


def test_short_name_keeps_only_the_real_name():
    from hlasys2_app.util import short_name

    assert short_name("Ondřej Pithart - Ondra Lhota") == "Ondřej Pithart"
    assert short_name("Ondřej Pithart") == "Ondřej Pithart"
    assert short_name("Systém") == "Systém"
    assert short_name("Real Name - nick - with dash") == "Real Name"
    assert short_name(None) == ""


def test_overview_shows_the_real_name_with_the_full_name_on_hover(app, db_path):
    from tests.test_deletion import login

    add_proposal(db_path, author_name="Jakub Novák - Jakub")
    with app.test_client() as client:
        login(client, DECIDER)
        body = client.get("/overview").get_data(as_text=True)

    assert '<td class="td-author" title="Jakub Novák - Jakub">Jakub Novák</td>' in body
