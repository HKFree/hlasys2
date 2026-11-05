"""
Route-level tests for the overview group filter and the vote permission check,
reusing the SQLite-backed fixtures from test_deletion.
"""
from tests.test_deletion import (  # noqa: F401 - fixtures
    app, db_path, add_proposal, login, raw, AUTHOR, DECIDER,
)


def vote_count(db_path, pid):
    conn = raw(db_path)
    n = conn.execute(
        "SELECT COUNT(*) FROM event WHERE proposal_id = ? AND decision IS NOT NULL",
        (pid,),
    ).fetchone()[0]
    conn.close()
    return n


def test_user_id_that_is_a_substring_of_a_decider_cannot_vote(app, db_path):
    pid = add_proposal(db_path)  # deciders include 277
    with app.test_client() as client:
        login(client, 27)
        client.post(f"/proposal/{pid}/quick-vote", data={"decision": "for"})
    assert vote_count(db_path, pid) == 0


def test_decider_can_vote(app, db_path):
    pid = add_proposal(db_path)
    with app.test_client() as client:
        login(client, DECIDER)
        client.post(f"/proposal/{pid}/quick-vote", data={"decision": "for"})
    assert vote_count(db_path, pid) == 1


def test_default_overview_shows_every_relevant_group(app, db_path):
    vv = add_proposal(db_path, type=0)
    pd = add_proposal(db_path, type=2)
    cs = add_proposal(db_path, type=3)
    so = add_proposal(db_path, type=1)
    with app.test_client() as client:
        login(client, AUTHOR)
        body = client.get("/overview").get_data(as_text=True)

    for pid in (vv, pd, cs):
        assert f'/proposal/{pid}"' in body
    assert f'/proposal/{so}"' not in body
    # Every default pill is on; turning one off links to the remaining two.
    for remaining in ("vvcs", "pdcs", "pdvv"):
        assert f'href="/overview/{remaining}"' in body
    # The archive pill is offered but off; turning it on shows only the archive.
    assert "group-so pill-off" in body
    assert 'href="/overview/so"' in body


def test_archive_can_be_turned_on(app, db_path):
    so = add_proposal(db_path, type=1)
    with app.test_client() as client:
        login(client, AUTHOR)
        body = client.get("/overview/so").get_data(as_text=True)

    assert f'/proposal/{so}"' in body
    assert "group-so pill-on" in body


def test_subset_filter_hides_other_groups(app, db_path):
    vv = add_proposal(db_path, type=0)
    pd = add_proposal(db_path, type=2)
    with app.test_client() as client:
        login(client, AUTHOR)
        body = client.get("/overview/pd").get_data(as_text=True)

    assert f'/proposal/{pd}"' in body
    assert f'/proposal/{vv}"' not in body
    # Turning off the only active pill goes back to everything.
    assert 'href="/overview"' in body


def test_rows_are_labelled_with_their_group(app, db_path):
    add_proposal(db_path, type=2)
    with app.test_client() as client:
        login(client, AUTHOR)
        body = client.get("/overview").get_data(as_text=True)

    assert "group-pd" in body
    assert 'class="group-prefix" title="Představenstvo družstva">PD<' in body
