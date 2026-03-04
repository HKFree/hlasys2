from flask import (
    Blueprint, flash, redirect, render_template, 
    session, request, url_for, current_app
)
import math, json, copy
from threading import Thread

from hlasys2_app.db import get_db
from hlasys2_app.util import (
    HkfreeRole, next_filter, overview_filter, can_vote, 
    is_proposal_accepted, userdb_api, get_undecided, calculate_acceptance_treshold
)
from hlasys2_app.forms import CreateProposalForm, CreateCommentForm
from hlasys2_app.notifications import notify_new_proposal
from hlasys2_app.decorators import login_required
from hlasys2_app import config

bp = Blueprint("proposals", __name__)


@bp.route("/overview", defaults={"filter": ""})
@bp.route("/overview/", defaults={"filter": ""})
@bp.route("/overview/<filter>")
@login_required
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
                p.id, p.author_name, p.author_id, p.subject, p.description, p.acceptance_treshold,
                p.cost, p.type, p.created, p.state, p.deciders,
                COALESCE(SUM(CASE WHEN e.decision = 1 THEN 1 END), 0) AS votes_for,
                COALESCE(SUM(CASE WHEN e.decision = 0 THEN 1 END), 0) AS votes_against
            FROM proposal p LEFT JOIN event e ON p.id = e.proposal_id
            WHERE p.id IN ({id_placeholders})
            GROUP BY p.id
            ORDER BY p.created DESC
        """
        for row in db.execute(data_sql, data_params).fetchall():
            proposal = dict(row)
            proposal["accepted"] = is_proposal_accepted(proposal)
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
@login_required
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
        user_voted=user_voted,
        user_id=user_id,
        HkfreeRole=HkfreeRole,
        users_change_state=config.USERS_CHANGE_STATE,
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
                "author_id": session["oidc_auth_profile"]["given_name"],
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
@login_required
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
                "comment": f"Změna stavu z '{current_state or 'Nic'}' na '{new_state}'",
            },
        )
        db.commit()
        flash("Stav návrhu byl změněn.", "success")

    return redirect(url_for("proposals.view_proposal", proposal_id=proposal_id))
