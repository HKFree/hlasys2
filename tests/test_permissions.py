import json

from hlasys2_app.util import can_delete_proposal

DECIDERS = {"277": "Jakub", "797": "zitnyp", "1980": "pavkriz"}


def make_proposal(**overrides):
    """A live, undecided VV proposal authored by 9000."""
    base = {
        "id": 1,
        "author_id": 9000,
        "type": 0,  # VV - in DECIDER_DELETE_TYPES
        "deciders": json.dumps(DECIDERS, ensure_ascii=False),
        "deleted": None,
        "decided": None,
    }
    base.update(overrides)
    return base


def test_author_can_delete():
    assert can_delete_proposal(9000, make_proposal()) is True


def test_decider_on_small_committee_can_delete():
    assert can_delete_proposal(277, make_proposal()) is True


def test_stranger_cannot_delete():
    assert can_delete_proposal(5555, make_proposal()) is False


def test_decider_on_cs_cannot_delete():
    """CS has ~116 deciders, so decider-delete is deliberately not granted."""
    assert can_delete_proposal(277, make_proposal(type=3)) is False


def test_author_of_cs_proposal_can_still_delete():
    assert can_delete_proposal(9000, make_proposal(type=3)) is True


def test_decided_proposal_cannot_be_deleted():
    assert can_delete_proposal(9000, make_proposal(decided="2026-01-01 00:00:00")) is False


def test_already_deleted_proposal_cannot_be_deleted():
    assert can_delete_proposal(9000, make_proposal(deleted="2026-01-01 00:00:00")) is False


def test_deciders_accepts_a_parsed_dict():
    """view_proposal parses deciders in place before rendering."""
    assert can_delete_proposal(277, make_proposal(deciders=dict(DECIDERS))) is True


def test_decider_check_is_not_a_substring_match():
    """User 27 must not inherit rights from decider 277 (cf. votes.py:100)."""
    assert can_delete_proposal(27, make_proposal()) is False
