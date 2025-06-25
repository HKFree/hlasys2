from flask import Blueprint, flash, redirect, render_template, session, request, url_for
import math

from hlasys2_app.db import get_db
from hlasys2_app.util import (
    HkfreeRole,
    next_filter,
    overview_filter,
    can_vote,
    is_proposal_accepted,
    userdb_api,
    user_voted,
)
from hlasys2_app.forms import CreateProposalForm, CreateCommentForm
from hlasys2_app import oidc
from hlasys2_app import config

bp = Blueprint("proposals", __name__)


@bp.route("/overview", defaults={"filter": ""})
@bp.route("/overview/", defaults={"filter": ""})
@bp.route("/overview/<filter>")
@oidc.require_login
def overview(filter):
    db = get_db()
    offset = request.args.get("offset", default=0, type=int)
    if offset < 0:
        offset = 0
    limit = 25  # Static limit

    # Get search query from request arguments
    search_query = request.args.get("search_query", default="").strip()
    sql_query_params = {} # To hold all :named parameters for SQL queries

    where_conditions = []
    
    # Filter conditions from overview_filter(filter)
    filter_sql_snippet = overview_filter(filter) 
    if filter_sql_snippet:
        condition_from_filter = filter_sql_snippet.strip()
        if condition_from_filter.upper().startswith("WHERE "):
            condition_from_filter = condition_from_filter[len("WHERE "):].strip() # Remove "WHERE "
        if condition_from_filter:
            where_conditions.append(f"({condition_from_filter})")

    # Standard condition: proposal not deleted
    where_conditions.append("proposal.deleted IS NULL")

    # Add search conditions if a search query is provided
    if search_query:
        where_conditions.append(
            "(proposal.subject LIKE :search_term OR proposal.description LIKE :search_term OR proposal.author_name LIKE :search_term)"
        )
        sql_query_params["search_term"] = f"%{search_query}%"
        
    final_where_clause = ""
    if where_conditions:
        final_where_clause = "WHERE " + " AND ".join(where_conditions)
    
    ids_query_sql = f"""
        SELECT proposal.id
        FROM proposal
        {final_where_clause}
        ORDER BY proposal.created DESC
        LIMIT :limit OFFSET :offset
    """
    
    # Prepare parameters for the ids_query
    current_ids_params = {"limit": limit, "offset": offset}
    if search_query:
        current_ids_params['limit'] = 10000
        
    current_ids_params.update(sql_query_params) # Add search_term if present

    proposal_ids_rows = db.execute(ids_query_sql, current_ids_params).fetchall()

    proposals_final_list = []

    if proposal_ids_rows:
        proposal_ids = [row["id"] for row in proposal_ids_rows]

        # Prepare named placeholders for the IN clause
        step2_in_clause_params = {}
        named_id_placeholders_list = []
        for i, pid in enumerate(proposal_ids):
            placeholder_name = f"pid_{i}"
            named_id_placeholders_list.append(f":{placeholder_name}")
            step2_in_clause_params[placeholder_name] = pid
        
        named_id_placeholders_str = ', '.join(named_id_placeholders_list)

        # --- Step 2: Fetch full details and vote counts for these specific IDs ---
        data_query = f"""
            SELECT
                p.id, p.author_name, p.author_id, p.subject, p.description, p.cost, p.type, p.created, p.state,
                COALESCE(SUM(CASE WHEN e.decision = 1 THEN 1 ELSE 0 END), 0) AS n_voted_for,
                COALESCE(SUM(CASE WHEN e.decision = 0 THEN 1 ELSE 0 END), 0) AS n_voted_against
            FROM
                proposal p
            LEFT JOIN
                event e ON p.id = e.proposal_id
            WHERE
                p.id IN ({named_id_placeholders_str})
            GROUP BY
                p.id, p.author_name, p.author_id, p.subject, p.description, p.cost, p.type, p.created
            ORDER BY
                p.created DESC
        """
        proposals_data = db.execute(data_query, step2_in_clause_params).fetchall()
        proposals_map = {row["id"]: dict(row) for row in proposals_data} # Ensure rows are dicts

        ordered_proposals_raw = []
        for pid in proposal_ids:
            if pid in proposals_map:
                ordered_proposals_raw.append(proposals_map[pid])

        for proposal_row_dict in ordered_proposals_raw:
            proposal_row_dict["accepted"] = is_proposal_accepted(
                proposal_row_dict["n_voted_for"],
                proposal_row_dict["n_voted_against"],
                proposal_row_dict["type"],
            )
            proposals_final_list.append(proposal_row_dict)

    # get total number of proposals matching the filter and search
    count_query_sql = f"SELECT COUNT(proposal.id) as count FROM proposal {final_where_clause}"
    
    # Parameters for count query are the same search params (overview_filter assumed to embed its values)
    total_proposals_row = db.execute(count_query_sql, sql_query_params).fetchone()
    n_proposals = total_proposals_row['count'] if total_proposals_row else 0
        
    # Calculate total_pages and current_page for pagination
    total_pages = 0
    if n_proposals > 0 and limit > 0:
        total_pages = math.ceil(n_proposals / limit)
    elif n_proposals == 0 : # If no proposals, still technically 0 or 1 page
        total_pages = 0 # Or 1, depending on desired display for no results

    current_page = 1
    if limit > 0 :
      current_page = math.floor(offset / limit) + 1
    
    if search_query:
        total_pages = 1
        
    return render_template(
        "proposals/ovreview.html",
        proposals=proposals_final_list,
        filter=filter,
        search_query=search_query,
        limit=limit,
        total_pages=int(total_pages),
        current_page=int(current_page),
        next_filter=next_filter, 
        HkfreeRole=HkfreeRole,
    )


@bp.route("/proposal/<int:proposal_id>")
@oidc.require_login
def one_proposal(proposal_id):
    db = get_db()

    proposal = db.execute(
        """
        SELECT proposal.id, author_name, author_id, subject, description, cost, type, created, deleted, state
        FROM proposal
        WHERE id = :proposal_id
        ORDER BY proposal.created DESC""",
        {"proposal_id": proposal_id},
    ).fetchone()

    if not proposal:
        flash("Takovej návrh neznám", "danger")
        return redirect("/")
    
    if proposal['deleted'] is not None:
        flash("Tento návrh byl smazán", "warning")
        return redirect("/")

    latest_votes_query = """
        SELECT e.author_id, e.author_name, e.decision, e.comment, e.created
        FROM event e
        JOIN (
            SELECT author_id, MAX(created) as max_created
            FROM event
            WHERE proposal_id = :proposal_id AND decision IS NOT NULL -- Only consider actual votes
            GROUP BY author_id
        ) latest ON e.author_id = latest.author_id AND e.created = latest.max_created
        WHERE e.proposal_id = :proposal_id AND e.decision IS NOT NULL
    """
    latest_votes = db.execute(
        latest_votes_query, {"proposal_id": proposal_id}
    ).fetchall()

    if config.DEBUG:
        print(
            f"DEBUG: All latest_votes for proposal {proposal_id}\nDEBUG: ", latest_votes
        )

    # Separate users based on their latest vote
    voted_for = [vote for vote in latest_votes if vote["decision"] == 1]
    voted_against = [vote for vote in latest_votes if vote["decision"] == 0]

    undeciders = userdb_api.not_sure_yet(voted_for, voted_against, proposal["type"])

    events = db.execute(
        """
        SELECT * FROM event 
        WHERE proposal_id = :proposal_id
        ORDER BY created DESC""",
        {"proposal_id": proposal_id},
    ).fetchall()

    accepted = is_proposal_accepted(
        len(voted_for), len(voted_against), proposal["type"]
    )
    user_id = int(session["oidc_auth_profile"]["given_name"])

    return render_template(
        "proposals/one.html",
        data=proposal,
        events=events,
        voted_for=voted_for,
        voted_against=voted_against,
        user_voted=user_voted(user_id, proposal["id"]),
        can_vote=can_vote(user_id, proposal),
        len=len,
        accepted=accepted,
        user_id=user_id,
        role_str=HkfreeRole(proposal["type"]).name.lower(),
        long_role_str=HkfreeRole(proposal["type"]).long_name,
        undeciders=undeciders,
        users_change_state=config.USERS_CHANGE_STATE,
    )


@bp.route("/proposal/create", methods=["GET", "POST"])
@oidc.require_login
def create_proposal():
    db = get_db()
    form: CreateProposalForm = CreateProposalForm()
    if form.validate_on_submit():
        db.execute(
            """ INSERT INTO proposal ('author_id', 'author_name', 'type', 'subject', 'description', 'cost')
            VALUES (:author_id, :author_name, :type, :subject, :description, :cost)""",
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
        last_id = db.execute(
            "SELECT id FROM proposal ORDER BY created DESC LIMIT 1"
        ).fetchone()
        flash("Návrh zapsán", "success")
        return redirect(f"/proposal/{last_id['id']}")
    else:
        return render_template("proposals/create.html", form=form)


@bp.route("/proposal/<int:proposal_id>/comment", methods=["GET", "POST"])
@oidc.require_login
def create_vote(proposal_id: int):
    db = get_db()
    form: CreateCommentForm = CreateCommentForm()
    if form.validate_on_submit():
        db.execute(
            """ INSERT INTO event ('proposal_id', 'author_id', 'author_name', 'comment')
            VALUES (:proposal_id, :author_id, :author_name, :comment)""",
            {
                "proposal_id": proposal_id,
                "author_id": int(session["oidc_auth_profile"]["given_name"]),
                "author_name": session["oidc_auth_profile"]["family_name"],
                "comment": form.comment.data,
            },
        )
        db.commit()
        flash("Komentář zapsán", "success")
        return redirect(f"/proposal/{proposal_id}")
    else:
        return render_template(
            "voting/comment.html", form=form, proposal_id=proposal_id
        )

@bp.route("/proposal/<int:proposal_id>/state/<new_state>", methods=["GET"])
@oidc.require_login
def change_state(proposal_id: int, new_state: str):
    db = get_db()
    
    if int(session["oidc_auth_profile"]["given_name"]) not in config.USERS_CHANGE_STATE:
        flash("Ty nemůžeš měnit stav", "danger")
        return redirect(f"/proposal/{proposal_id}")
    

    curr_state = db.execute("SELECT state FROM proposal WHERE id = :proposal_id", {"proposal_id": proposal_id}).fetchone()
    if new_state == curr_state['state'] or (new_state == 'Nic' and not curr_state['state']):
        flash("Stejný stav", "danger")
        return redirect(f"/proposal/{proposal_id}")
    
    db.execute("UPDATE proposal SET state = :new_state WHERE id =  :proposal_id", {"new_state": None if new_state == 'Nic' else new_state, "proposal_id": proposal_id})

    db.execute(
        """ INSERT INTO event ('proposal_id', 'author_id', 'author_name', 'comment')
        VALUES (:proposal_id, :author_id, :author_name, :comment)""",
        {
            "proposal_id": proposal_id,
            "author_id": int(session["oidc_auth_profile"]["given_name"]),
            "author_name": session["oidc_auth_profile"]["family_name"],
            "comment": f"Změna stavu z {curr_state['state']} na {new_state}",
        },
    )
    db.commit()
    flash("Změna zapsána", "success")
    return redirect(f"/proposal/{proposal_id}")

