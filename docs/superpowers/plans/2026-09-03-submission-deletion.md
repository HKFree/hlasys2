# Submission Deletion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a proposal's author, or a decider on a small committee, soft-delete an undecided proposal; log who did it; expose the deleted set through a "Koš" toggle on the overview.

**Architecture:** No schema change — `proposal.deleted` already exists. A new `deletion` blueprint mirrors the structure of `votes.py`. The deletion writes `proposal.deleted` and an `event` row sharing one microsecond-precision timestamp, so the deleter is recoverable by joining `event.created = proposal.deleted` entirely in SQL. `overview()` gains a koš mode, with its WHERE/ORDER/pagination construction extracted into a pure, unit-testable helper.

**Tech Stack:** Flask 3, Flask-WTF, SQLite (`sqlite3` stdlib, `dict_factory`), Jinja2, Poetry, pytest.

Spec: `docs/superpowers/specs/2026-09-03-submission-deletion-design.md`

---

## File Structure

| File | Responsibility |
|---|---|
| `hlasys2_app/util.py` | `can_delete_proposal()` — the permission predicate, pure |
| `hlasys2_app/deletion.py` | **new** — confirm + delete routes, the only writer of `proposal.deleted` |
| `hlasys2_app/proposals.py` | `_build_overview_query()` (pure), koš mode in `overview()`, deleted-aware `view_proposal` |
| `hlasys2_app/forms.py` | `DeleteProposalForm` |
| `hlasys2_app/users.py` | timeline excludes deleted proposals |
| `hlasys2_app/config.example.py` | documents `DECIDER_DELETE_TYPES` |
| `hlasys2_app/__init__.py` | registers the blueprint |
| `templates/proposals/delete.html` | **new** — confirmation page |
| `templates/proposals/overview.html` | koš toggle + conditional columns |
| `templates/proposals/one.html` | deleted banner, hides state buttons |
| `templates/proposals/decisions.html` | delete button, hides actions when deleted |
| `static/style.css` | `.d-deleted-banner`, `.btn-delete` |
| `tests/` | **new** — pytest for the two pure functions |

Run all commands from the repo root, through Poetry: `poetry run <cmd>`.

---

### Task 1: Test scaffolding

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/__init__.py`, `tests/conftest.py`

- [ ] **Step 1: Add pytest as a dev dependency**

```bash
poetry add --group dev pytest
```

- [ ] **Step 2: Create the test package**

`tests/__init__.py` — empty file.

`tests/conftest.py`:

```python
"""
The functions under test are pure and need no Flask app context, but importing
hlasys2_app.util pulls in hlasys2_app.config, which must exist.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
```

- [ ] **Step 3: Verify pytest runs**

Run: `poetry run pytest -q`
Expected: `no tests ran`

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml poetry.lock tests/
git commit -m "test: add pytest dev dependency and test package"
```

---

### Task 2: `can_delete_proposal()`

**Files:**
- Modify: `hlasys2_app/util.py`
- Test: `tests/test_permissions.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_permissions.py`:

```python
import json

import pytest

from hlasys2_app.util import can_delete_proposal

DECIDERS = {"277": "Jakub", "797": "zitnyp", "1980": "pavkriz"}


def make_proposal(**overrides):
    """A live, undecided VV proposal authored by 9000."""
    base = {
        "id": 1,
        "author_id": 9000,
        "type": 0,                      # VV - in DECIDER_DELETE_TYPES
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
    """CS has 116 deciders, so decider-delete is deliberately not granted."""
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `poetry run pytest tests/test_permissions.py -q`
Expected: FAIL — `ImportError: cannot import name 'can_delete_proposal'`

- [ ] **Step 3: Implement**

Append to `hlasys2_app/util.py`:

```python
def can_delete_proposal(user_id: int, proposal: dict) -> bool:
    """
    Whether user_id may soft-delete this proposal.

    Allowed only while the proposal is live and undecided, and only for its
    author or for a decider on a small committee. CS is excluded from the
    decider case on purpose - it has ~116 deciders, which would put deletion of
    somebody else's proposal in far too many hands.

    Args:
        user_id (int): The acting user.
        proposal (dict): Proposal row. 'deciders' may be the raw JSON string or
            an already-parsed dict, because view_proposal parses it in place.

    Returns:
        bool: True if deletion is permitted.
    """
    if proposal["deleted"] is not None or proposal["decided"] is not None:
        return False

    if int(proposal["author_id"]) == int(user_id):
        return True

    # Read through getattr: config.py is bind-mounted read-only in production
    # and will not contain this key on the first deploy.
    decider_types = getattr(config, "DECIDER_DELETE_TYPES", [0, 1, 2])
    if int(proposal["type"]) not in decider_types:
        return False

    deciders = proposal["deciders"]
    if isinstance(deciders, str):
        deciders = json.loads(deciders)

    # Dict key lookup, never a substring test against the raw JSON.
    return str(user_id) in deciders
```

- [ ] **Step 4: Run to verify it passes**

Run: `poetry run pytest tests/test_permissions.py -q`
Expected: `9 passed`

- [ ] **Step 5: Commit**

```bash
git add hlasys2_app/util.py tests/test_permissions.py
git commit -m "feat: add can_delete_proposal permission predicate"
```

---

### Task 3: Extract `_build_overview_query()`

**Files:**
- Modify: `hlasys2_app/proposals.py:21-127`
- Test: `tests/test_overview_query.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_overview_query.py`:

```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `poetry run pytest tests/test_overview_query.py -q`
Expected: FAIL — `ImportError: cannot import name '_build_overview_query'`

- [ ] **Step 3: Implement the helper**

Insert into `hlasys2_app/proposals.py`, above `overview()`:

```python
def _build_overview_query(
    filter: str, search_query: str, deleted: bool, page: int, limit: int = 25
):
    """
    Build the WHERE clause, bound parameters, ORDER BY and pagination shared by
    the live overview and the koš.

    The caller supplies its own SELECT list: the live overview aggregates votes,
    the koš does not. Returns params WITHOUT :limit/:offset so the same dict can
    be reused for the COUNT query.

    Returns:
        tuple: (where_clause, params, order_by, limit, offset)
    """
    params = {}
    where_conditions = ["p.deleted IS NOT NULL" if deleted else "p.deleted IS NULL"]

    filter_sql = overview_filter(filter)
    if filter_sql:
        where_conditions.append(filter_sql.replace("WHERE", "").strip())

    # The koš has no search box; ignore a stray search_query there.
    searching = bool(search_query) and not deleted
    if searching:
        where_conditions.append(
            "(p.subject LIKE :search OR p.description LIKE :search"
            " OR p.author_name LIKE :search)"
        )
        params["search"] = f"%{search_query}%"

    where_clause = f"WHERE {' AND '.join(where_conditions)}"
    order_by = "ORDER BY p.deleted DESC" if deleted else "ORDER BY p.created DESC"

    offset = (page - 1) * limit if page > 0 else 0
    if searching:
        # Search shows every hit on one page.
        limit, offset = 10000, 0

    return where_clause, params, order_by, limit, offset
```

- [ ] **Step 4: Run to verify it passes**

Run: `poetry run pytest tests/test_overview_query.py -q`
Expected: `8 passed`

- [ ] **Step 5: Commit**

```bash
git add hlasys2_app/proposals.py tests/test_overview_query.py
git commit -m "refactor: extract _build_overview_query from overview()"
```

---

### Task 4: `DeleteProposalForm`

**Files:**
- Modify: `hlasys2_app/forms.py`

- [ ] **Step 1: Add the form**

Append to `hlasys2_app/forms.py`:

```python
class DeleteProposalForm(FlaskForm):
    reason = TextAreaField(
        "Důvod smazání (nepovinný)",
        name="reason",
        render_kw={"rows": 3, "placeholder": "Např. duplicita, viz návrh 1230"},
    )
```

- [ ] **Step 2: Verify it imports**

Run: `poetry run python -c "from hlasys2_app.forms import DeleteProposalForm; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add hlasys2_app/forms.py
git commit -m "feat: add DeleteProposalForm"
```

---

### Task 5: The `deletion` blueprint

**Files:**
- Create: `hlasys2_app/deletion.py`
- Modify: `hlasys2_app/__init__.py`

- [ ] **Step 1: Create the blueprint**

`hlasys2_app/deletion.py` — full content:

```python
from datetime import datetime

from flask import (
    Blueprint, flash, redirect, render_template, session, url_for
)

from hlasys2_app.db import get_db
from hlasys2_app.decorators import login_required
from hlasys2_app.forms import DeleteProposalForm
from hlasys2_app.util import HkfreeRole, can_delete_proposal

bp = Blueprint("deletion", __name__)


def _load_deletable_proposal(proposal_id: int, user_id: int):
    """
    Load the proposal and run the pre-delete checks. Mirrors
    votes._load_votable_proposal.

    Returns:
        tuple: (proposal_or_None, redirect_response_or_None)
    """
    db = get_db()
    proposal = db.execute(
        "SELECT * FROM proposal WHERE id = :id", {"id": proposal_id}
    ).fetchone()

    if not proposal:
        flash("Takový návrh neexistuje.", "warning")
        return None, redirect(url_for("proposals.overview"))

    detail = redirect(url_for("proposals.view_proposal", proposal_id=proposal_id))

    if proposal["deleted"] is not None:
        flash("Tento návrh už je smazaný.", "warning")
        return None, detail

    if proposal["decided"] is not None:
        flash("Odhlasovaný návrh nelze smazat.", "danger")
        return None, detail

    if not can_delete_proposal(user_id, proposal):
        flash("Nemáš oprávnění smazat tento návrh.", "danger")
        return None, detail

    return proposal, None


def _count_votes(db, proposal_id: int) -> dict:
    """Latest vote per user, split for/against - drives the confirmation warning."""
    return db.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN e.decision = 1 THEN 1 END), 0) AS votes_for,
            COALESCE(SUM(CASE WHEN e.decision = 0 THEN 1 END), 0) AS votes_against
        FROM event e
        JOIN (
            SELECT author_id, MAX(created) AS max_created
            FROM event
            WHERE proposal_id = :pid AND decision IS NOT NULL
            GROUP BY author_id
        ) latest ON e.author_id = latest.author_id AND e.created = latest.max_created
        WHERE e.proposal_id = :pid AND e.decision IS NOT NULL
        """,
        {"pid": proposal_id},
    ).fetchone()


@bp.route("/proposal/<int:proposal_id>/delete", methods=["GET", "POST"])
@login_required
def delete_proposal(proposal_id: int):
    """Confirmation screen (GET) and the soft delete itself (POST)."""
    user_id = int(session["oidc_auth_profile"]["preferred_username"])
    user_name = session["oidc_auth_profile"]["family_name"]

    proposal, redir = _load_deletable_proposal(proposal_id, user_id)
    if redir is not None:
        return redir

    db = get_db()
    form = DeleteProposalForm()

    if form.validate_on_submit():
        # A single timestamp for both writes. The deletion event is later
        # identified by `event.created = proposal.deleted`, so these two values
        # MUST stay byte-identical. See the design spec.
        ts = datetime.now().isoformat(sep=" ", timespec="microseconds")

        reason = (form.reason.data or "").strip()
        comment = f"Návrh smazal {user_name}."
        if reason:
            comment += f" Důvod: {reason}"

        # The guard lives in the WHERE clause so a double submit cannot produce
        # a second event.
        cursor = db.execute(
            """UPDATE proposal SET deleted = :ts
               WHERE id = :id AND deleted IS NULL AND decided IS NULL""",
            {"ts": ts, "id": proposal_id},
        )
        if cursor.rowcount != 1:
            db.rollback()
            flash("Návrh se mezitím změnil, smazání se neprovedlo.", "warning")
            return redirect(
                url_for("proposals.view_proposal", proposal_id=proposal_id)
            )

        db.execute(
            """INSERT INTO event
                   (proposal_id, author_id, author_name, decision, comment, created)
               VALUES (:pid, :uid, :uname, NULL, :comment, :ts)""",
            {
                "pid": proposal_id,
                "uid": user_id,
                "uname": user_name,
                "comment": comment,
                "ts": ts,
            },
        )
        db.commit()
        flash("Návrh byl smazán.", "success")
        return redirect(url_for("proposals.view_proposal", proposal_id=proposal_id))

    return render_template(
        "proposals/delete.html",
        proposal=proposal,
        form=form,
        votes=_count_votes(db, proposal_id),
        HkfreeRole=HkfreeRole,
    )
```

- [ ] **Step 2: Register it**

In `hlasys2_app/__init__.py`, after the `votes` blueprint registration (line ~42-44), add:

```python
    from . import deletion

    app.register_blueprint(deletion.bp)
```

- [ ] **Step 3: Verify the app still builds**

Run: `poetry run python -c "
from hlasys2_app import create_app
app = create_app()
print([str(r) for r in app.url_map.iter_rules() if 'delete' in str(r)])
"`
Expected: a rule for `/proposal/<int:proposal_id>/delete`

- [ ] **Step 4: Commit**

```bash
git add hlasys2_app/deletion.py hlasys2_app/__init__.py
git commit -m "feat: add deletion blueprint with confirm and soft-delete routes"
```

---

### Task 6: Confirmation template

**Files:**
- Create: `hlasys2_app/templates/proposals/delete.html`

- [ ] **Step 1: Create the template**

```html
{% extends 'base.html' %}

{% block header %}
    <h1>{% block title %}Opravdu smazat návrh?{% endblock %}</h1>
{% endblock %}

{% block content %}
    <div id="d-one-bot">
        <p><b>„{{ proposal.subject }}"</b></p>
        <p>
            <small>
                návrh <b>{{ proposal.id }}</b> pro
                <strong>{{ HkfreeRole(proposal.type).long_name }}</strong> ·
                vložil {{ proposal.author_name }}
                dne {{ proposal.created.strftime('%d.%m.%Y') }}
            </small>
        </p>
    </div>

    {% set total_votes = votes.votes_for + votes.votes_against %}
    {% if total_votes > 0 %}
    <div class="d-one-decision-row d-one-rejected">
        <b>⚠ U návrhu už {% if total_votes == 1 %}je 1 hlas{% else %}jsou {{ total_votes }} hlasy{% endif %}
        ({{ votes.votes_for }} PRO, {{ votes.votes_against }} PROTI).</b><br>
        Smazáním zmizí návrh i s nimi z přehledu.
    </div>
    {% endif %}

    <hr>

    <form method="post">
        {{ form.csrf_token }}
        <p>
            {{ form.reason.label }}<br>
            {{ form.reason() }}
        </p>
        <div class="d-vote-btn">
            <button type="submit" class="btn-delete">Smazat návrh</button>
            <a class="state-btn"
               href="{{ url_for('proposals.view_proposal', proposal_id=proposal.id) }}">Zpět</a>
        </div>
    </form>

    <p><small><b>Smazání nelze vrátit zpět.</b></small></p>
{% endblock %}
```

- [ ] **Step 2: Commit**

```bash
git add hlasys2_app/templates/proposals/delete.html
git commit -m "feat: add delete confirmation template"
```

---

### Task 7: Koš mode in `overview()`

**Files:**
- Modify: `hlasys2_app/proposals.py` — `overview()`
- Modify: `hlasys2_app/templates/proposals/overview.html`

- [ ] **Step 1: Add the deleted-row fetch helper**

Insert into `hlasys2_app/proposals.py`, below `_build_overview_query`:

```python
def _fetch_deleted_proposals(db, where_clause, params, order_by, limit, offset):
    """
    Rows for the koš. The deleter is recovered by matching the deletion event on
    `event.created = proposal.deleted` - the two values are written from one
    Python timestamp inside a single transaction (see deletion.py). Rows hidden
    during the 2005-data migration have no such event and yield NULL.
    """
    sql = f"""
        SELECT
            p.id, p.subject, p.created, p.author_id, p.author_name,
            p.cost, p.type, p.deleted,
            (SELECT e.author_id FROM event e
              WHERE e.proposal_id = p.id AND e.created = p.deleted
              LIMIT 1) AS deleted_by_id,
            (SELECT e.author_name FROM event e
              WHERE e.proposal_id = p.id AND e.created = p.deleted
              LIMIT 1) AS deleted_by_name
        FROM proposal p
        {where_clause}
        {order_by}
        LIMIT :limit OFFSET :offset
    """
    query_params = {**params, "limit": limit, "offset": offset}
    return [dict(row) for row in db.execute(sql, query_params).fetchall()]
```

- [ ] **Step 2: Rewrite `overview()` to use the helpers**

Replace the body of `overview()` (currently `proposals.py:25-127`) with:

```python
def overview(filter):
    """Paginated overview of proposals, with filtering, search and a koš mode."""
    db = get_db()
    show_deleted = request.args.get("deleted", default="") == "1"
    # The koš has no search box, so never honour a stray search_query there.
    search_query = (
        "" if show_deleted else request.args.get("search_query", default="").strip()
    )

    # A plain integer search jumps straight to that proposal.
    if search_query.isdigit():
        proposal_row = db.execute(
            "SELECT id FROM proposal WHERE id = :id", {"id": int(search_query)}
        ).fetchone()
        if proposal_row:
            return redirect(
                url_for("proposals.view_proposal", proposal_id=proposal_row["id"])
            )

    page = request.args.get("page", default=1, type=int)
    where_clause, params, order_by, limit, offset = _build_overview_query(
        filter, search_query, show_deleted, page
    )

    count_sql = f"SELECT COUNT(p.id) AS count FROM proposal p {where_clause}"
    total_proposals = db.execute(count_sql, params).fetchone()["count"]
    total_pages = math.ceil(total_proposals / limit) if total_proposals > 0 else 0
    if search_query:
        total_pages = 1

    if show_deleted:
        proposals = _fetch_deleted_proposals(
            db, where_clause, params, order_by, limit, offset
        )
    else:
        proposals = _fetch_live_proposals(
            db, where_clause, params, order_by, limit, offset
        )

    return render_template(
        "proposals/overview.html",
        proposals=proposals,
        filter=filter,
        search_query=search_query,
        show_deleted=show_deleted,
        total_pages=int(total_pages),
        current_page=int(page),
        next_filter=next_filter,
    )
```

- [ ] **Step 3: Move the existing live-list query into `_fetch_live_proposals`**

Insert into `hlasys2_app/proposals.py`, below `_fetch_deleted_proposals`. This is the
two-step ID-then-aggregate query lifted verbatim from the old `overview()` body:

```python
def _fetch_live_proposals(db, where_clause, params, order_by, limit, offset):
    """
    Rows for the live overview, with vote tallies. Two-step: page the IDs first,
    then aggregate only those - much cheaper than paginating across the join.
    """
    ids_sql = f"""
        SELECT p.id FROM proposal p
        {where_clause}
        {order_by}
        LIMIT :limit OFFSET :offset
    """
    id_params = {**params, "limit": limit, "offset": offset}
    proposal_ids = [row["id"] for row in db.execute(ids_sql, id_params).fetchall()]

    if not proposal_ids:
        return []

    id_placeholders = ", ".join([f":id_{i}" for i in range(len(proposal_ids))])
    data_params = {f"id_{i}": pid for i, pid in enumerate(proposal_ids)}

    data_sql = f"""
        SELECT
            p.id, p.author_name, p.author_id, p.subject, p.description,
            p.acceptance_treshold, p.cost, p.type, p.created, p.state,
            p.deciders, p.decided,
            COALESCE(SUM(CASE WHEN e.decision = 1 THEN 1 END), 0) AS votes_for,
            COALESCE(SUM(CASE WHEN e.decision = 0 THEN 1 END), 0) AS votes_against
        FROM proposal p LEFT JOIN event e ON p.id = e.proposal_id
        WHERE p.id IN ({id_placeholders})
        GROUP BY p.id
        {order_by}
    """

    user_id = int(session["oidc_auth_profile"]["preferred_username"])
    voted_sql = f"""
        SELECT DISTINCT proposal_id FROM event
        WHERE author_id = :uid AND decision IS NOT NULL
          AND proposal_id IN ({id_placeholders})
    """
    voted_ids = {
        row["proposal_id"]
        for row in db.execute(voted_sql, {**data_params, "uid": user_id}).fetchall()
    }

    proposals = []
    for row in db.execute(data_sql, data_params).fetchall():
        proposal = dict(row)
        proposal["accepted"] = is_proposal_accepted(proposal)
        deciders = json.loads(proposal["deciders"])
        proposal["user_pending"] = (
            str(user_id) in deciders
            and proposal["id"] not in voted_ids
            and proposal["decided"] is None
        )
        proposals.append(proposal)
    return proposals
```

- [ ] **Step 4: Update the overview template**

In `hlasys2_app/templates/proposals/overview.html`, replace the filter strip
(lines 13-31) so every link carries the koš flag, and append the toggle:

```html
{% set kos = 1 if show_deleted else None %}
<div class="d-row-toggle">
    <a href="{{ url_for('proposals.overview', filter=next_filter(filter, 'pd'), deleted=kos) }}">
        <span>{% if 'pd' in filter %}✔{% else %}✖{% endif %}</span> Představenstvo Družstva
    </a>
    <a href="{{ url_for('proposals.overview', filter=next_filter(filter, 'vv'), deleted=kos) }}">
        <span>{% if 'vv' in filter %}✔{% else %}✖{% endif %}</span> Výkonný Výbor
    </a>
    <a href="{{ url_for('proposals.overview', filter=next_filter(filter, 'cs'), deleted=kos) }}">
        <span>{% if 'cs' in filter %}✔{% else %}✖{% endif %}</span> Členové spolku
    </a>
    <a href="{{ url_for('proposals.overview', filter=next_filter(filter, 'cd'), deleted=kos) }}">
        <span>{% if 'cd' in filter %}✔{% else %}✖{% endif %}</span> Členové družstva
    </a>
    <a href="{{ url_for('proposals.overview', filter=next_filter(filter, 'so'), deleted=kos) }}">
        <span>{% if 'so' in filter %}✔{% else %}✖{% endif %}</span> Správce Oblastí (archiv)
    </a>
    <a href="{{ url_for('proposals.overview', filter=filter, deleted=None if show_deleted else 1) }}">
        <span>{% if show_deleted %}✔{% else %}✖{% endif %}</span> 🗑 Koš
    </a>
</div>
```

Wrap the search block (lines 51-58) in `{% if not show_deleted %}` … `{% endif %}`.

Add `deleted=kos` to every `url_for('proposals.overview', ...)` call in both
pagination blocks.

Change the page title block to read:

```html
<h1>{% block title %}{% if show_deleted %}Koš{% else %}Přehled návrhů{% endif %}{% if filter in filter_labels %} — {{ filter_labels[filter] }}{% endif %}{% if current_page > 1 %} (str. {{ current_page }}){% endif %}{% endblock %}</h1>
```

Replace the table (lines 60-94) with a two-mode version:

```html
<table class="t-proposals">
    <thead>
        <tr>
            <th>Návrh</th>
            <th>Vytvořeno</th>
            <th>Navrhovatel</th>
            {% if show_deleted %}
            <th>Smazal</th>
            <th>Smazáno</th>
            {% else %}
            <th>Odhad ceny</th>
            <th>Stav</th>
            {% endif %}
        </tr>
    </thead>
    <tbody>
        {% for p in proposals %}
            {% if show_deleted %}
            <tr class="tr-proposal tr-proposal-deleted">
                <td>
                    <a href="{{ url_for('proposals.view_proposal', proposal_id=p.id) }}">
                        <b>{{ p.subject }}</b>
                    </a>
                </td>
                <td><small class="s-overview-date">{{ p.created.strftime('%d.%m.') }}{% if p.created.year != now_year %}{{ p.created.strftime('%Y') }}{% endif %}</small></td>
                <td>{{ p.author_name | truncate(20) }}</td>
                <td>
                    {% if p.deleted_by_name %}
                        <a href="{{ url_for('users.user_overview', user_id=p.deleted_by_id) }}">{{ p.deleted_by_name | truncate(20) }}</a>
                    {% else %}
                        <span class="text-muted">—</span>
                    {% endif %}
                </td>
                <td><small class="s-overview-date">{{ p.deleted.strftime('%d.%m.%Y %H:%M') }}</small></td>
            </tr>
            {% else %}
            {% set pending_cls = ' tr-user-pending' if p.user_pending else '' %}
            {% if p.accepted == True %}
            <tr class="tr-proposal tr-proposal-accepted{{ pending_cls }}">
            {% elif p.accepted == False %}
            <tr class="tr-proposal tr-proposal-rejected{{ pending_cls }}">
            {% else %}
            <tr class="tr-proposal tr-proposal-undecided{{ pending_cls }}">
            {% endif %}
                <td>
                    <a href="{{ url_for('proposals.view_proposal', proposal_id=p.id) }}">
                        <b>{{ p.subject }}</b>
                    </a>
                </td>
                <td><small class="s-overview-date">{{ p.created.strftime('%d.%m.') }}{% if p.created.year != now_year %}{{ p.created.strftime('%Y') }}{% endif %}</small></td>
                <td>{{ p.author_name | truncate(20) }}</td>
                <td>{{ "{:,}".format(p.cost) }} Kč</td>
                <td>{{ p.state or '' }}</td>
            </tr>
            {% endif %}
        {% else %}
            <tr><td colspan="5">{% if show_deleted %}Koš je prázdný.{% else %}Nebyly nalezeny žádné návrhy.{% endif %}</td></tr>
        {% endfor %}
    </tbody>
</table>
```

- [ ] **Step 5: Verify the pure helper tests still pass**

Run: `poetry run pytest -q`
Expected: `17 passed`

- [ ] **Step 6: Commit**

```bash
git add hlasys2_app/proposals.py hlasys2_app/templates/proposals/overview.html
git commit -m "feat: add kos mode to the proposal overview"
```

---

### Task 8: Deleted proposals render read-only

**Files:**
- Modify: `hlasys2_app/proposals.py` — `view_proposal`
- Modify: `hlasys2_app/templates/proposals/one.html`
- Modify: `hlasys2_app/templates/proposals/decisions.html`

- [ ] **Step 1: Stop redirecting, load the deletion event**

In `view_proposal`, delete the redirect block (`proposals.py:143-145`) and add,
after `proposal = dict(proposal_row)`:

```python
    # The deletion event is the one whose created matches proposal.deleted; both
    # were written from a single timestamp in deletion.py. Matched in SQL so no
    # Python datetime adapter is involved.
    deletion_event = None
    if proposal["deleted"] is not None:
        deletion_event = db.execute(
            """SELECT e.author_id, e.author_name, e.comment
               FROM event e
               JOIN proposal p ON p.id = e.proposal_id AND e.created = p.deleted
               WHERE p.id = :pid
               LIMIT 1""",
            {"pid": proposal_id},
        ).fetchone()
```

Add to the `render_template` call:

```python
        deletion_event=deletion_event,
        can_delete=can_delete_proposal(user_id, proposal_row),
```

Extend the `hlasys2_app.util` import at `proposals.py:9-12` with `can_delete_proposal`.

Note `can_delete_proposal` is passed `proposal_row`, not `proposal`, because
`proposal["deciders"]` is parsed in place at line 172 — the raw row is unambiguous.

- [ ] **Step 2: Add the banner and hide state buttons in `one.html`**

Immediately after `{% block content %}`:

```html
    {% if proposal.deleted %}
    <div class="d-deleted-banner">
        🗑 <b>Návrh byl smazán {{ proposal.deleted.strftime('%d.%m.%Y v %H:%M') }}</b>
        {% if deletion_event %}<br>{{ deletion_event.comment }}{% endif %}
    </div>
    {% endif %}
```

Change the state-button guard from `{% if user_id in users_change_state %}` to:

```html
    {% if user_id in users_change_state and not proposal.deleted %}
```

- [ ] **Step 3: Gate the actions in `decisions.html`**

Wrap the whole `<div class="d-vote-btn"> … </div>` block (lines 17-52) in
`{% if not proposal.deleted %}` … `{% endif %}`, and add the delete button just
before the closing `</div>` of `d-vote-btn`:

```html
    {% if can_delete %}
        <form action="{{ url_for('deletion.delete_proposal', proposal_id=proposal.id) }}" method="get">
            <button type="submit" class="btn-delete">Smazat návrh</button>
        </form>
    {% endif %}
```

- [ ] **Step 4: Add the styles**

Append to `hlasys2_app/static/style.css`:

```css
.d-deleted-banner {
    background-color: var(--danger-bg);
    color: var(--danger-text);
    border: 1px solid var(--danger-text);
    border-radius: 4px;
    padding: 10px 14px;
    margin-bottom: 14px;
}

.btn-delete {
    background-color: var(--danger-text);
    color: #fff;
}

.tr-proposal-deleted td,
.tr-proposal-deleted td a {
    color: var(--text-muted);
}
```

Check the variable names against the existing file first and substitute the real
ones if they differ.

- [ ] **Step 5: Verify**

Run: `poetry run pytest -q`
Expected: `17 passed`

- [ ] **Step 6: Commit**

```bash
git add hlasys2_app/proposals.py hlasys2_app/templates/proposals/one.html \
        hlasys2_app/templates/proposals/decisions.html hlasys2_app/static/style.css
git commit -m "feat: render deleted proposals read-only with a deletion banner"
```

---

### Task 9: Timeline excludes deleted proposals

**Files:**
- Modify: `hlasys2_app/users.py:24-50`

- [ ] **Step 1: Filter the probes and the timeline union**

Replace the two probe queries and the timeline query:

```python
    user_event = db.execute(
        """SELECT e.* FROM event e
           JOIN proposal p ON p.id = e.proposal_id
           WHERE e.author_id = :user_id AND p.deleted IS NULL
           LIMIT 1""",
        {"user_id": user_id},
    ).fetchone()
    user_proposal = db.execute(
        """SELECT * FROM proposal
           WHERE author_id = :user_id AND deleted IS NULL
           LIMIT 1""",
        {"user_id": user_id},
    ).fetchone()
```

and add `WHERE proposal.deleted IS NULL` / `WHERE deleted IS NULL` to the two
halves of the UNION:

```python
    timeline = db.execute(
        """
        SELECT * FROM (
            SELECT event.author_id AS user_id, event.created, proposal.subject AS events_subject, proposal_id, decision, comment, NULL AS subject, NULL AS proposals_id
            FROM event
            JOIN proposal ON event.proposal_id = proposal.id
            WHERE proposal.deleted IS NULL
            UNION ALL
            SELECT author_id AS user_id, created, NULL AS events_subject, NULL AS proposal_id, NULL AS decision, NULL AS comment, subject, id AS proposals_id
            FROM proposal
            WHERE deleted IS NULL
        )
        WHERE user_id = :user_id
        ORDER BY created DESC""",
        {"user_id": user_id},
    ).fetchall()
```

- [ ] **Step 2: Commit**

```bash
git add hlasys2_app/users.py
git commit -m "fix: exclude deleted proposals from user timelines"
```

---

### Task 10: Document the config key

**Files:**
- Modify: `hlasys2_app/config.example.py`

- [ ] **Step 1: Add the key**

After `USERS_CHANGE_STATE = [9000]`:

```python
# Proposal types whose deciders may delete an undecided proposal, on top of its
# author. 0 = VV, 1 = SO, 2 = PD, 3 = CS, 4 = CD. CS is left out on purpose - it
# has ~116 deciders. Optional; defaults to [0, 1, 2] when absent.
DECIDER_DELETE_TYPES = [0, 1, 2]
```

Mirror it into the local `hlasys2_app/config.py` (gitignored) for dev.

- [ ] **Step 2: Commit**

```bash
git add hlasys2_app/config.example.py
git commit -m "docs: document DECIDER_DELETE_TYPES config key"
```

---

### Task 11: End-to-end verification against a scratch database

**Files:** none modified

- [ ] **Step 1: Build a scratch DB and exercise the flow**

Copy `instance/hlas.sqlite` to a temp path, point `DATABASE` at it, and use the
Flask test client with `HLASYS_ENV=development` to:

1. `GET /overview/vv` — 200, no deleted rows
2. `GET /overview/vv?deleted=1` — 200, shows legacy rows with `—` for Smazal
3. `GET /proposal/<undecided_id>/delete` as the author — 200
4. `POST` it with a reason — 302, `proposal.deleted` set, exactly one new event
5. Confirm `event.created == proposal.deleted` for that row
6. `GET /proposal/<id>` — 200 with the banner, no vote buttons
7. `POST /proposal/<id>/quick-vote` — blocked
8. `GET /proposal/<decided_id>/delete` — 302 with "Odhlasovaný návrh nelze smazat."
9. `GET /proposal/<id>/delete` as a stranger — 302 with the permission flash
10. Double-`POST` the delete — second one produces no extra event

- [ ] **Step 2: Commit nothing; record the result**

---

### Task 12: Version bump

**Files:**
- Modify: `pyproject.toml`, `hlasys2_app/version.py`

- [ ] **Step 1: Bump to 2.1.0**

Set `version = "2.1.0"` in `pyproject.toml` and `HLASYS2_VERSION = "2.1.0"` in
`hlasys2_app/version.py`.

- [ ] **Step 2: Verify**

Run: `poetry run python -c "from hlasys2_app.version import HLASYS2_VERSION; print(HLASYS2_VERSION)"`
Expected: `2.1.0`

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml hlasys2_app/version.py
git commit -m "version bump to 2.1.0"
```
