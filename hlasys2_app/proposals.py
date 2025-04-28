from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
    abort,
)
from math import ceil

from hlasys2_app.db import get_db
from . import util
from .util import HkfreeRole
from hlasys2_app.forms import CreateProposalForm, CreateCommentForm

bp = Blueprint("proposals", __name__)

# TODO: send no cache headers


@bp.route("/overview")
def overview_redir():
    db = get_db()
    proposals = db.execute(
        f"""
        SELECT proposal.id, author_name, author_id, subject, description, cost, type, created,
        ( SELECT COUNT(*) FROM event WHERE event.proposal_id = proposal.id AND event.decision = 1 ) AS n_voted_for,
        ( SELECT COUNT(*) FROM event WHERE event.proposal_id = proposal.id AND event.decision = 0 ) AS n_voted_against
        FROM proposal
        ORDER BY proposal.created DESC"""
    ).fetchall()

    print(proposals)

    return render_template("proposals/ovreview.html", proposals=proposals)


@bp.route("/overview/<query_filter>")
def overview(query_filter):
    db = get_db()
    filter_str = str()

    f = {"vv": "vv" in query_filter, "so": "so" in query_filter}
    if not f["vv"] and not f["so"]:
        return redirect("/overview/vv+so")
    elif f["vv"] and not f["so"]:
        filter_str = "WHERE proposal.type = 0"
    elif not f["vv"] and f["so"]:
        filter_str = "WHERE proposal.type = 1"

    proposals = db.execute(
        f"""
        SELECT proposal.id, user.name, user.email, user.id as user_id, subject, description, cost, type, created,
        ( SELECT COUNT(*) FROM event WHERE event.proposal_id = proposal.id AND event.decision = 1 ) AS n_voted_for,
        ( SELECT COUNT(*) FROM event WHERE event.proposal_id = proposal.id AND event.decision = 0 ) AS n_voted_against
        FROM proposal
        LEFT JOIN user ON proposal.author_id = user.id
        {filter_str}
        ORDER BY proposal.created DESC"""
    ).fetchall()

    for p in proposals:
        p["accepted"] = None
        if p["type"] == 0:  # VV
            num_vv = util.num_vv()

            if p["n_voted_for"] >= 4:
                p["accepted"] = True
            elif p["n_voted_against"] >= 4:
                p["accepted"] = False

        else:  # SO
            num_so = util.num_so()
            if p["n_voted_for"] >= ceil(num_so / 2):
                p["accepted"] = True
            elif p["n_voted_against"] > ceil(num_so / 2):
                p["accepted"] = False

    return render_template("proposals/ovreview.html", proposals=proposals, filter=f)


@bp.route("/proposal/<int:proposal_id>")
def one_proposal(proposal_id):
    db = get_db()

    proposal = db.execute(
        """
        SELECT proposal.id as proposal_id, proposal.subject, proposal.description, proposal.cost, proposal.type,
        proposal.created, author_id, author_name
        FROM proposal 
        WHERE proposal.id = :proposal_id""",
        {"proposal_id": proposal_id},
    ).fetchone()

    if not proposal:
        # flash("neni")
        return redirect("/")

    events = db.execute(
        """
        SELECT * FROM event 
        WHERE proposal_id = :proposal_id ORDER BY created DESC""",
        {"proposal_id": proposal_id},
    ).fetchall()

    voted_for = db.execute(
        """SELECT * FROM event
        WHERE proposal_id = :proposal_id AND decision = 1""",
        {"proposal_id": proposal_id},
    ).fetchall()

    voted_against = db.execute(
        """SELECT * FROM event
        WHERE proposal_id = :proposal_id AND decision = 0""",
        {"proposal_id": proposal_id},
    ).fetchall()

    print("for", len(voted_for))
    print("against", len(voted_against))

    accepted = None
    # if proposal["type"] == 0:  # VV
    #     num_vv = util.num_vv()

    #     if len(voted_for) >= 4:
    #         accepted = True
    #     elif len(voted_against) >= 4:
    #         accepted = False

    # elif proposal["type"] == 1:  # SO
    #     num_so = util.num_so()
    #     if len(voted_for) >= ceil(num_so / 2):
    #         accepted = True
    #     elif len(voted_against) > ceil(num_so / 2):
    #         accepted = False
    
    # else:
    #     # TODO implement predstavenstov
    #     0 == 0

    return render_template(
        "proposals/one.html",
        data=proposal,
        events=events,
        voted_for=voted_for,
        voted_against=voted_against,
        # can_vote=util.can_vote(session["user_id"], proposal_id),
        len=len,
        accepted=accepted,
    )


@bp.route("/proposal/create", methods=["GET", "POST"])
def create_proposal(): 
    db = get_db()
    form: CreateProposalForm = CreateProposalForm()
    if form.validate_on_submit():
        db.execute(
            """ INSERT INTO proposal ('author_id', 'type', 'subject', 'description', 'cost')
            VALUES (:author_id, :type, :subject, :description, :cost)""",
            {
                "author_id": session['user_id'],
                "type": form.type.data,
                "subject": form.subject.data,
                "description": form.description.data,
                "cost": form.cost.data
            }
        )
        db.commit()
        return redirect(f"/user/{session['user_id']}")
    else:
        return render_template("proposals/create.html", form=form)

@bp.route("/proposal/<int:proposal_id>/comment", methods=["GET", "POST"])
def create_vote(proposal_id: int): 
    db = get_db()
    form: CreateCommentForm = CreateCommentForm()
    if form.validate_on_submit():
        print(form.data)
        db.execute(
            """ INSERT INTO event ('proposal_id', 'user_id', 'comment')
            VALUES (:proposal_id, :user_id, :comment)""",
            {
                "proposal_id": proposal_id,
                "user_id": session['user_id'],
                "comment": form.comment.data
            }
        )
        db.commit()
        return redirect(f"/proposal/{proposal_id}")
    else:
        return render_template("voting/comment.html", form=form, proposal_id=proposal_id)

