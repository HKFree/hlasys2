from flask import (
    Blueprint, flash, redirect, render_template, 
    session, request, url_for
)
import math

from hlasys2_app.db import get_db
from hlasys2_app.util import (
    HkfreeRole, next_filter, overview_filter, can_vote, 
    is_proposal_accepted, userdb_api, user_voted
)
from hlasys2_app.forms import CreateProposalForm, CreateCommentForm
from hlasys2_app import oidc, config

bp = Blueprint("proposals", __name__)


@bp.route("/overview", defaults={"filter": ""})
@bp.route("/overview/", defaults={"filter": ""})
@bp.route("/overview/<filter>")
@oidc.require_login
def overview(filter):
    """Displays a paginated overview of proposals, with filtering and searching."""
    db = get_db()
    search_query = request.args.get("search_query", default="").strip()
    page = request.args.get("page", default=1, type=int)
    limit = 25
    offset = (page - 1) * limit if page > 0 else 0

    params = {}
    where_conditions = ["p.deleted IS NULL"]

    # Apply category filter and search term to the query
    filter_sql = overview_filter(filter)
    if filter_sql:
        where_conditions.append(filter_sql.replace("WHERE", "").strip())

    if search_query:
        search_clause = "(p.subject LIKE :search OR p.description LIKE :search OR p.author_name LIKE :search)"
        where_conditions.append(search_clause)
        params["search"] = f"%{search_query}%"

    where_clause = f"WHERE {' AND '.join(where_conditions)}"

    # First, get the total count for pagination
    count_sql = f"SELECT COUNT(p.id) AS count FROM proposal p {where_clause}"
    total_proposals = db.execute(count_sql, params).fetchone()['count']
    total_pages = math.ceil(total_proposals / limit) if total_proposals > 0 else 0
    
    # When searching, show all results on a single page
    if search_query:
        limit = 10000 
        offset = 0
        total_pages = 1

    # This two-step query is more efficient for pagination with joins.
    # 1. Fetch only the IDs for the current page.
    ids_sql = f"""
        SELECT p.id FROM proposal p
        {where_clause}
        ORDER BY p.created DESC
        LIMIT :limit OFFSET :offset
    """
    params.update({"limit": limit, "offset": offset})
    proposal_ids = [row["id"] for row in db.execute(ids_sql, params).fetchall()]
    
    proposals = []
    if proposal_ids:
        # 2. Fetch the full data only for the selected IDs.
        id_placeholders = ", ".join([f":id_{i}" for i in range(len(proposal_ids))])
        data_params = {f"id_{i}": pid for i, pid in enumerate(proposal_ids)}
        
        data_sql = f"""
            SELECT
                p.id, p.author_name, p.author_id, p.subject, p.description, 
                p.cost, p.type, p.created, p.state,
                COALESCE(SUM(CASE WHEN e.decision = 1 THEN 1 END), 0) AS votes_for,
                COALESCE(SUM(CASE WHEN e.decision = 0 THEN 1 END), 0) AS votes_against
            FROM proposal p LEFT JOIN event e ON p.id = e.proposal_id
            WHERE p.id IN ({id_placeholders})
            GROUP BY p.id
            ORDER BY p.created DESC
        """
        for row in db.execute(data_sql, data_params).fetchall():
            proposal = dict(row)
            proposal["accepted"] = is_proposal_accepted(
                proposal["votes_for"], proposal["votes_against"], proposal["type"]
            )
            proposals.append(proposal)

    return render_template(
        "proposals/overview.html",
        proposals=proposals,
        filter=filter,
        search_query=search_query,
        total_pages=int(total_pages),
        current_page=int(page),
        next_filter=next_filter,
    )


@bp.route("/proposal/<int:proposal_id>")
@oidc.require_login
def view_proposal(proposal_id):
    """Displays a single proposal and its associated events and votes."""
    db = get_db()
    user_id = int(session["oidc_auth_profile"]["given_name"])

    proposal_row = db.execute("SELECT * FROM proposal WHERE id = :id", {"id": proposal_id}).fetchone()

    if not proposal_row:
        flash("Takový návrh neexistuje.", "danger")
        return redirect(url_for("proposals.overview"))

    if proposal_row['deleted'] is not None:
        flash("Tento návrh byl smazán.", "warning")
        return redirect(url_for("proposals.overview"))

    proposal = dict(proposal_row)

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
    proposal['accepted'] = is_proposal_accepted(
        len(proposal['voted_for']), len(proposal['voted_against']), proposal["type"]
    )
    
    events = db.execute(
        "SELECT * FROM event WHERE proposal_id = :id ORDER BY created DESC",
        {"id": proposal_id}
    ).fetchall()

    return render_template(
        "proposals/one.html",
        proposal=proposal,
        events=events,
        undecided_voters=userdb_api.not_sure_yet(
            proposal['voted_for'], proposal['voted_against'], proposal["type"]
        ),
        can_vote=can_vote(user_id, proposal),
        user_id=user_id,
        HkfreeRole=HkfreeRole,
        users_change_state=config.USERS_CHANGE_STATE,
    )


@bp.route("/proposal/create", methods=["GET", "POST"])
@oidc.require_login
def create_proposal():
    """Handles the creation of a new proposal."""
    form = CreateProposalForm()
    print(form.cost)
    print(form.validate_on_submit())
    if form.validate_on_submit():
        db = get_db()
        cursor = db.execute(
            """
            INSERT INTO proposal (author_id, author_name, type, subject, description, cost)
            VALUES (:author_id, :author_name, :type, :subject, :description, :cost)
            """,
            {
                "author_id": session["oidc_auth_profile"]["given_name"],
                "author_name": session["oidc_auth_profile"]["family_name"],
                "type": form.type.data,
                "subject": form.subject.data,
                "description": form.description.data,
                "cost": form.cost.data,
            },
        )
        db.commit()
        
        flash("Návrh byl úspěšně vytvořen.", "success")
        return redirect(url_for("proposals.view_proposal", proposal_id=cursor.lastrowid))
        
    return render_template("proposals/create.html", form=form)


@bp.route("/proposal/<int:proposal_id>/comment", methods=["GET", "POST"])
@oidc.require_login
def add_comment(proposal_id: int):
    """Handles adding a comment to a proposal."""
    form = CreateCommentForm()
    if form.validate_on_submit():
        db = get_db()
        db.execute(
            """
            INSERT INTO event (proposal_id, author_id, author_name, comment)
            VALUES (:pid, :uid, :uname, :comment)
            """,
            {
                "pid": proposal_id,
                "uid": int(session["oidc_auth_profile"]["given_name"]),
                "uname": session["oidc_auth_profile"]["family_name"],
                "comment": form.comment.data,
            },
        )
        db.commit()
        flash("Komentář byl přidán.", "success")
        return redirect(url_for("proposals.view_proposal", proposal_id=proposal_id))

    return render_template("voting/comment.html", form=form, proposal_id=proposal_id)


@bp.route("/proposal/<int:proposal_id>/state/<new_state>")
@oidc.require_login
def change_state(proposal_id: int, new_state: str):
    """Changes the state of a proposal (e.g., 'Ordered'). For authorized users only."""
    user_id = int(session["oidc_auth_profile"]["given_name"])
    if user_id not in config.USERS_CHANGE_STATE:
        flash("Nemáte oprávnění měnit stav návrhu.", "danger")
        return redirect(url_for("proposals.view_proposal", proposal_id=proposal_id))

    db = get_db()
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
                "comment": f"Změna stavu z '{current_state or 'Žádný'}' na '{new_state}'",
            },
        )
        db.commit()
        flash("Stav návrhu byl změněn.", "success")

    return redirect(url_for("proposals.view_proposal", proposal_id=proposal_id))