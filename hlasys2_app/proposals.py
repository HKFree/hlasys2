from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    session,
)

from hlasys2_app.db import get_db
from hlasys2_app.util import HkfreeRole, next_filter, overview_filter, can_vote, is_proposal_accepted, userdb_api, user_voted
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
    proposals = db.execute(
        f"""
        SELECT proposal.id, author_name, author_id, subject, description, cost, type, created,
        ( SELECT COUNT(1) FROM event WHERE event.proposal_id = proposal.id AND event.decision = 1 ) AS n_voted_for,
        ( SELECT COUNT(1) FROM event WHERE event.proposal_id = proposal.id AND event.decision = 0 ) AS n_voted_against
        FROM proposal 
        {overview_filter(filter)}
        ORDER BY proposal.created DESC""",
    ).fetchall()

    for proposal in proposals:
        proposal['accepted'] = is_proposal_accepted(
            proposal['n_voted_for'], proposal['n_voted_against'], proposal['type'])

    return render_template("proposals/ovreview.html", proposals=proposals, filter=filter, next_filter=next_filter, HkfreeRole=HkfreeRole)


@bp.route("/proposal/<int:proposal_id>")
@oidc.require_login
def one_proposal(proposal_id):
    db = get_db()

    proposal = db.execute(
        """
        SELECT proposal.id, author_name, author_id, subject, description, cost, type, created
        FROM proposal
        WHERE id = :proposal_id
        ORDER BY proposal.created DESC""",
        {"proposal_id": proposal_id},
    ).fetchone()

    if not proposal:
        flash("Takovej návrh neznám", "danger")
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
        latest_votes_query, {"proposal_id": proposal_id}).fetchall()

    if config.DEBUG:
        print(
            f"DEBUG: All latest_votes for proposal {proposal_id}\nDEBUG: ", latest_votes)

    # Separate users based on their latest vote
    voted_for = [vote for vote in latest_votes if vote['decision'] == 1]
    voted_against = [vote for vote in latest_votes if vote['decision'] == 0]

    undeciders = userdb_api.not_sure_yet(
        voted_for, voted_against, proposal['type'])

    events = db.execute(
        """
        SELECT * FROM event 
        WHERE proposal_id = :proposal_id
        ORDER BY created DESC""",
        {"proposal_id": proposal_id},
    ).fetchall()

    accepted = is_proposal_accepted(
        len(voted_for), len(voted_against), proposal['type'])
    user_id = session["oidc_auth_profile"]["given_name"]

    return render_template(
        "proposals/one.html",
        data=proposal,
        events=events,
        voted_for=voted_for,
        voted_against=voted_against,
        user_voted=user_voted(user_id, proposal['id']),
        can_vote=can_vote(user_id, proposal),
        len=len,
        accepted=accepted,
        role_str=HkfreeRole(proposal['type']).name.lower(),
        long_role_str=HkfreeRole(proposal['type']).long_name,
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
            "SELECT id FROM proposal ORDER BY created DESC LIMIT 1").fetchone()
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
