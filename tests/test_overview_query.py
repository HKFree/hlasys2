from hlasys2_app.proposals import _build_overview_query


def test_live_mode_excludes_deleted():
    where, params, order_by, limit, offset = _build_overview_query("vv", "", False, 1)
    assert "p.deleted IS NULL" in where
    assert order_by == "ORDER BY p.created DESC"
    assert (limit, offset) == (25, 0)
    assert params == {}


def test_kos_mode_selects_only_deleted_newest_first():
    where, params, order_by, limit, offset = _build_overview_query("vv", "", True, 1)
    assert "p.deleted IS NOT NULL" in where
    assert order_by == "ORDER BY p.deleted DESC"


def test_type_filter_is_applied():
    where, _, _, _, _ = _build_overview_query("vv", "", False, 1)
    assert "type IN (0)" in where


def test_empty_filter_matches_nothing():
    where, _, _, _, _ = _build_overview_query("", "", False, 1)
    assert "1 = 0" in where


def test_search_adds_a_clause_and_collapses_pagination():
    where, params, _, limit, offset = _build_overview_query("vv", "switch", False, 3)
    assert "p.subject LIKE :search" in where
    assert params["search"] == "%switch%"
    assert (limit, offset) == (10000, 0)


def test_kos_ignores_search_because_the_box_is_hidden():
    where, params, _, limit, offset = _build_overview_query("vv", "switch", True, 3)
    assert "LIKE :search" not in where
    assert params == {}
    assert (limit, offset) == (25, 50)


def test_pagination_offset():
    _, _, _, limit, offset = _build_overview_query("vv", "", False, 3)
    assert (limit, offset) == (25, 50)


def test_page_zero_does_not_produce_a_negative_offset():
    _, _, _, _, offset = _build_overview_query("vv", "", False, 0)
    assert offset == 0
