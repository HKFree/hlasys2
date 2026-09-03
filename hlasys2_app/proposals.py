from flask import (
    Blueprint, flash, redirect, render_template, 
    session, request, url_for, current_app
)
import math, json, copy
from threading import Thread

from hlasys2_app.db import get_db
from hlasys2_app.util import (
    HkfreeRole, next_filter, overview_filter, can_vote, can_delete_proposal,
    is_proposal_accepted, userdb_api, get_undecided, calculate_acceptance_treshold
)
from hlasys2_app.forms import CreateProposalForm, CreateCommentForm, QuickVoteForm
from hlasys2_app.notifications import notify_new_proposal
from hlasys2_app.decorators import login_required
from hlasys2_app import config

bp = Blueprint("proposals", __name__)


def _is_deleted(db, proposal_id: int) -> bool:
    """Whether the proposal exists and has been soft-deleted."""
    row = db.execute(
        "SELECT deleted FROM proposal WHERE id = :id", {"id": proposal_id}
    ).fetchone()
    return bool(row) and row["deleted"] is not None


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
        tuple: (where_clause, params, order_by, limit, offset, searching)
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

    return where_clause, params, order_by, limit, offset, searching


def _fetch_deleted_proposals(db, where_clause, params, order_by, limit, offset):
    """
    Rows for the koš. The deleter is recovered by matching the deletion event on
    `event.created = proposal.deleted` - the two values are written from one
    Python timestamp inside a single transaction (see deletion.py). Rows hidden
    during the 2005-data migration have no such event and yield NULL.
    """
    # One LEFT JOIN rather than a correlated subquery per column: `event` has no
    # index, so each subquery would cost a full scan. GROUP BY collapses the
    # (impossible in practice) case of two events sharing the exact timestamp.
    sql = f"""
        SELECT
            p.id, p.subject, p.created, p.author_id, p.author_name,
            p.cost, p.type, p.deleted,
            d.author_id AS deleted_by_id,
            d.author_name AS deleted_by_name
        FROM proposal p
        LEFT JOIN event d
               ON d.proposal_id = p.id AND d.created = p.deleted
        {where_clause}
        GROUP BY p.id
        {order_by}
        LIMIT :limit OFFSET :offset
    """
    query_params = {**params, "limit": limit, "offset": offset}
    return [dict(row) for row in db.execute(sql, query_params).fetchall()]


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

    # Identify proposals where the current user already voted, in one batched query
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


@bp.route("/overview", defaults={"filter": ""})
@bp.route("/overview/", defaults={"filter": ""})
@bp.route("/overview/<filter>")
@login_required
def overview(filter):
    """Paginated overview of proposals, with filtering, search and a koš mode."""
    db = get_db()
    show_deleted = request.args.get("deleted", default="") == "1"
    # The koš has no search box, so never honour a stray search_query there.
    search_query = (
        "" if show_deleted else request.args.get("search_query", default="").strip()
    )

    # If the search query is a plain integer, try direct proposal ID lookup
    if search_query.isdigit():
        proposal_row = db.execute(
            "SELECT id FROM proposal WHERE id = :id", {"id": int(search_query)}
        ).fetchone()
        if proposal_row:
            return redirect(
                url_for("proposals.view_proposal", proposal_id=proposal_row["id"])
            )

    page = request.args.get("page", default=1, type=int)
    where_clause, params, order_by, limit, offset, searching = _build_overview_query(
        filter, search_query, show_deleted, page
    )

    # First, get the total count for pagination
    count_sql = f"SELECT COUNT(p.id) AS count FROM proposal p {where_clause}"
    total_proposals = db.execute(count_sql, params).fetchone()["count"]
    if searching:
        # When searching, every hit goes on a single page.
        total_pages = 1
    else:
        total_pages = math.ceil(total_proposals / limit) if total_proposals > 0 else 0

    fetch = _fetch_deleted_proposals if show_deleted else _fetch_live_proposals
    proposals = fetch(db, where_clause, params, order_by, limit, offset)

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


@bp.route("/proposal/<int:proposal_id>")
@login_required
def view_proposal(proposal_id):
    """Displays a single proposal and its associated events and votes."""
    db = get_db()
    user_id = int(session["oidc_auth_profile"]["preferred_username"])

    proposal_row = db.execute("SELECT * FROM proposal WHERE id = :id", {"id": proposal_id}).fetchone()

    if not proposal_row:
        flash("Takový návrh neexistuje.", "danger")
        return redirect(url_for("proposals.overview"))

    proposal = dict(proposal_row)

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

    # This query efficiently finds the latest vote for each user on this proposal.
    latest_votes_sql = """
        SELECT e.author_id, e.author_name, e.decision, e.comment
        FROM event e
        JOIN (
            SELECT author_id, MAX(created) AS max_created
            FROM event
            WHERE proposal_id = :pid AND decision IS NOT NULL
            GROUP BY author_id
        ) latest ON e.author_id = latest.author_id AND e.created = latest.max_created
        WHERE e.proposal_id = :pid AND e.decision IS NOT NULL
    """
    latest_votes = db.execute(latest_votes_sql, {"pid": proposal_id}).fetchall()

    proposal['voted_for'] = [v for v in latest_votes if v["decision"] == 1]
    proposal['voted_against'] = [v for v in latest_votes if v["decision"] == 0]
    proposal['accepted'] = is_proposal_accepted(proposal)
    
    events = db.execute(
        "SELECT * FROM event WHERE proposal_id = :id ORDER BY created DESC",
        {"id": proposal_id}
    ).fetchall()

    proposal['deciders'] = json.loads(proposal['deciders'])

    user_voted = user_id in [v["author_id"] for v in proposal['voted_for'] + proposal['voted_against']]

    return render_template(
        "proposals/one.html",
        proposal=proposal,
        events=events,
        undecided_voters=get_undecided(proposal),
        can_vote=(str(user_id) in proposal['deciders']),
        # proposal_row, not proposal: deciders is parsed in place above.
        can_delete=can_delete_proposal(user_id, proposal_row),
        deletion_event=deletion_event,
        user_voted=user_voted,
        user_id=user_id,
        HkfreeRole=HkfreeRole,
        users_change_state=config.USERS_CHANGE_STATE,
        quick_vote_form=QuickVoteForm(),
    )


@bp.route("/proposal/create", methods=["GET", "POST"])
@login_required
def create_proposal():
    """Handles the creation of a new proposal."""
    form = CreateProposalForm()
    
    if form.validate_on_submit():
        db = get_db()
        deciders = userdb_api.get_deciders(int(form.type.data))

        cursor = db.execute(
            """
            INSERT INTO proposal (author_id, author_name, type, subject, description, cost, deciders, acceptance_treshold)
            VALUES (:author_id, :author_name, :type, :subject, :description, :cost, :deciders, :acceptance_treshold)
            """,
            {
                "author_id": session["oidc_auth_profile"]["preferred_username"],
                "author_name": session["oidc_auth_profile"]["family_name"],
                "type": form.type.data,
                "subject": form.subject.data,
                "description": form.description.data,
                "cost": form.cost.data,
                "deciders": json.dumps(deciders, ensure_ascii=False),
                "acceptance_treshold": calculate_acceptance_treshold(form.acceptance.data, deciders)
            },
        )
        db.commit()
        flash("Návrh byl úspěšně vytvořen.", "success")
        
        try:
            author_fullname = session["oidc_auth_profile"]["family_name"]
            full_url = f"{config.APP_BASE_URL}{url_for('proposals.view_proposal', proposal_id=cursor.lastrowid)}"
            # full_url = url_for('proposals.view_proposal', proposal_id=new_proposal_id, _external=True)
            
            thr = Thread(
                target=notify_new_proposal, 
                args=(
                    HkfreeRole(int(form.type.data)), 
                    cursor.lastrowid, 
                    form.subject.data, 
                    author_fullname, 
                    form.cost.data, 
                    form.description.data,
                    full_url
                )
            )
            thr.start()
        except Exception as e:
            print(f"ERROR create_proposal: {e}")
            
        return redirect(url_for("proposals.view_proposal", proposal_id=cursor.lastrowid))
        
    return render_template("proposals/create.html", form=form)


@bp.route("/proposal/<int:proposal_id>/comment", methods=["GET", "POST"])
@login_required
def add_comment(proposal_id: int):
    """Handles adding a comment to a proposal."""
    db = get_db()

    # A deleted proposal is inert. Enforced here, not just by hiding the button.
    if _is_deleted(db, proposal_id):
        flash("Tento návrh byl smazán, nelze do něj přidávat komentáře.", "warning")
        return redirect(url_for("proposals.view_proposal", proposal_id=proposal_id))

    form = CreateCommentForm()
    if form.validate_on_submit():
        db.execute(
            """
            INSERT INTO event (proposal_id, author_id, author_name, comment)
            VALUES (:pid, :uid, :uname, :comment)
            """,
            {
                "pid": proposal_id,
                "uid": int(session["oidc_auth_profile"]["preferred_username"]),
                "uname": session["oidc_auth_profile"]["family_name"],
                "comment": form.comment.data,
            },
        )
        db.commit()
        flash("Komentář byl přidán.", "success")
        return redirect(url_for("proposals.view_proposal", proposal_id=proposal_id))

    return render_template("voting/comment.html", form=form, proposal_id=proposal_id)


@bp.route("/proposal/<int:proposal_id>/state/<new_state>")
@login_required
def change_state(proposal_id: int, new_state: str):
    """Changes the state of a proposal (e.g., 'Ordered'). For authorized users only."""
    user_id = int(session["oidc_auth_profile"]["preferred_username"])
    if user_id not in config.USERS_CHANGE_STATE:
        flash("Nemáte oprávnění měnit stav návrhu.", "danger")
        return redirect(url_for("proposals.view_proposal", proposal_id=proposal_id))

    db = get_db()

    # A deleted proposal is inert. Enforced here, not just by hiding the buttons.
    if _is_deleted(db, proposal_id):
        flash("Tento návrh byl smazán, nelze měnit jeho stav.", "warning")
        return redirect(url_for("proposals.view_proposal", proposal_id=proposal_id))

    current_state = db.execute(
        "SELECT state FROM proposal WHERE id = :id", {"id": proposal_id}
    ).fetchone()["state"]
    
    # 'Nic' from the URL means setting the state to NULL
    new_state_value = None if new_state == 'Nic' else new_state

    if new_state_value == current_state:
        flash("Nový stav je stejný jako aktuální.", "info")
    else:
        db.execute(
            "UPDATE proposal SET state = :new_state WHERE id = :id",
            {"new_state": new_state_value, "id": proposal_id},
        )
        # Log the state change as a system event
        db.execute(
            """
            INSERT INTO event (proposal_id, author_id, author_name, comment)
            VALUES (:pid, :uid, :uname, :comment)
            """,
            {
                "pid": proposal_id, "uid": user_id, 
                "uname": session["oidc_auth_profile"]["family_name"],
                "comment": f"Změna stavu z '{current_state or 'Nic'}' na '{new_state}'",
            },
        )
        db.commit()
        flash("Stav návrhu byl změněn.", "success")

    return redirect(url_for("proposals.view_proposal", proposal_id=proposal_id))
