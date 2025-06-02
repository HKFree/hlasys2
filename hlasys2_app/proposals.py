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
    limit = 25

    print("limit ", limit, " offset ", offset)

    ids_query = f"""
        SELECT proposal.id
        FROM proposal
        {overview_filter(filter)} AND proposal.deleted IS NULL
        ORDER BY proposal.created DESC
        LIMIT :limit OFFSET :offset
    """
    proposal_ids_rows = db.execute(
        ids_query, {"limit": limit, "offset": offset}
    ).fetchall()

    proposals_final_list = []

    if proposal_ids_rows:
        proposal_ids = [row["id"] for row in proposal_ids_rows]

        # Create a string of placeholders for the IN clause, e.g., "(?, ?, ?)"
        placeholders = ", ".join(["?"] * len(proposal_ids))

        # Fetch full details and vote counts for these specific IDs
        data_query = f"""
            SELECT
                p.id, p.author_name, p.author_id, p.subject, p.description, p.cost, p.type, p.created,
                COALESCE(SUM(CASE WHEN e.decision = 1 THEN 1 ELSE 0 END), 0) AS n_voted_for,
                COALESCE(SUM(CASE WHEN e.decision = 0 THEN 1 ELSE 0 END), 0) AS n_voted_against
            FROM
                proposal p
            LEFT JOIN
                event e ON p.id = e.proposal_id
            WHERE
                p.id IN ({placeholders})
            GROUP BY
                p.id, p.author_name, p.author_id, p.subject, p.description, p.cost, p.type, p.created
            ORDER BY
                p.created DESC  -- Re-apply order to be sure, or order by p.id sequence from previous query
        """

        # Parameters for data_query are the proposal_ids
        proposals_data = db.execute(data_query, proposal_ids).fetchall()
        proposals_map = {row["id"]: row for row in proposals_data}

        ordered_proposals_raw = []
        for pid in proposal_ids:
            if pid in proposals_map:
                ordered_proposals_raw.append(proposals_map[pid])

        # Process 'accepted' status
        for proposal_row in ordered_proposals_raw:
            proposal_dict = dict(proposal_row)
            proposal_dict["accepted"] = is_proposal_accepted(
                proposal_dict["n_voted_for"],
                proposal_dict["n_voted_against"],
                proposal_dict["type"],
            )
            proposals_final_list.append(proposal_dict)

    n_proposals = db.execute(f"SELECT COUNT(*) as count FROM proposal {overview_filter(filter)}").fetchone()['count']
        
    return render_template(
        "proposals/ovreview.html",
        proposals=proposals_final_list,
        filter=filter,
        next_filter=next_filter,
        HkfreeRole=HkfreeRole,
        limit=limit,
        total_pages=math.floor(n_proposals / limit),
        current_page=math.ceil(offset / limit) + 1,
    )


@bp.route("/proposal/<int:proposal_id>")
@oidc.require_login
def one_proposal(proposal_id):
    db = get_db()

    proposal = db.execute(
        """
        SELECT proposal.id, author_name, author_id, subject, description, cost, type, created, deleted
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
    user_id = session["oidc_auth_profile"]["given_name"]

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
        role_str=HkfreeRole(proposal["type"]).name.lower(),
        long_role_str=HkfreeRole(proposal["type"]).long_name,
        undeciders=undeciders,
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
