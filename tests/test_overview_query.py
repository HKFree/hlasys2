from hlasys2_app.proposals import _build_overview_query
from hlasys2_app.util import parse_filter, toggle_filter, filter_to_url


def test_live_mode_excludes_deleted():
    where, params, order_by, limit, offset, _ = _build_overview_query("vv", "", False, 1)
    assert "p.deleted IS NULL" in where
    assert order_by == "ORDER BY p.created DESC"
    assert (limit, offset) == (25, 0)
    assert params == {"type_0": 0}


def test_kos_mode_selects_only_deleted_newest_first():
    where, params, order_by, limit, offset, _ = _build_overview_query("vv", "", True, 1)
    assert "p.deleted IS NOT NULL" in where
    assert order_by == "ORDER BY p.deleted DESC"


def test_type_filter_is_applied():
    where, params, _, _, _, _ = _build_overview_query("vv", "", False, 1)
    assert "p.type IN (:type_0)" in where
    assert params == {"type_0": 0}


def test_empty_filter_selects_the_default_groups():
    where, params, _, _, _, _ = _build_overview_query("", "", False, 1)
    assert "p.type IN (:type_0, :type_1, :type_2)" in where
    assert sorted(params.values()) == [0, 2, 3]  # VV, PD, CS


def test_parse_filter_accepts_combinations_and_old_urls():
    assert parse_filter("pd") == ["pd"]
    assert parse_filter("vvpd") == ["pd", "vv"]
    assert parse_filter("vvsopd") == ["pd", "vv", "so"]


def test_parse_filter_falls_back_to_defaults():
    assert parse_filter("") == ["pd", "vv", "cs"]
    assert parse_filter("xx") == ["pd", "vv", "cs"]


def test_default_selection_has_an_empty_url():
    assert filter_to_url(["cs", "vv", "pd"]) == ""
    assert filter_to_url(["vv", "pd"]) == "pdvv"


def test_toggle_turns_a_group_off_and_on():
    assert toggle_filter(["pd", "vv", "cs"], "vv") == "pdcs"
    assert toggle_filter(["pd", "cs"], "vv") == ""


def test_toggling_off_the_last_group_selects_all():
    assert toggle_filter(["cs"], "cs") == ""


def test_archive_turns_the_rest_off():
    assert toggle_filter(["pd", "vv", "cs"], "so") == "so"
    assert toggle_filter(["pd"], "so") == "so"


def test_turning_the_archive_off_selects_all():
    assert toggle_filter(["so"], "so") == ""


def test_any_other_group_turns_the_archive_off():
    assert toggle_filter(["so"], "pd") == "pd"
    assert toggle_filter(["so"], "vv") == "vv"


def test_search_adds_a_clause_and_collapses_pagination():
    where, params, _, limit, offset, _ = _build_overview_query("vv", "switch", False, 3)
    assert "p.subject LIKE :search" in where
    assert params["search"] == "%switch%"
    assert (limit, offset) == (10000, 0)


def test_kos_ignores_search_because_the_box_is_hidden():
    where, params, _, limit, offset, _ = _build_overview_query("vv", "switch", True, 3)
    assert "LIKE :search" not in where
    assert params == {"type_0": 0}
    assert (limit, offset) == (25, 50)


def test_pagination_offset():
    _, _, _, limit, offset, _ = _build_overview_query("vv", "", False, 3)
    assert (limit, offset) == (25, 50)


def test_page_zero_does_not_produce_a_negative_offset():
    _, _, _, _, offset, _ = _build_overview_query("vv", "", False, 0)
    assert offset == 0
