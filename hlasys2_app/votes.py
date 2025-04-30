from hlasys2_app.util import can_vote
from hlasys2_app.db import get_db
from flask import Blueprint, render_template, redirect, session, request, flash
from hlasys2_app.forms import VoteDecisionForm
from hlasys2_app import oidc

bp = Blueprint("votes", __name__)


@bp.route("/proposal/<int:proposal_id>/vote", methods=["GET", "POST"])
@oidc.require_login
def vote_on_proposal(proposal_id: int):
    db = get_db()
    current_user = session["oidc_auth_profile"]
    form: VoteDecisionForm = VoteDecisionForm()
    proposal = db.execute(
        """
        SELECT * FROM proposal 
        WHERE proposal.id = :proposal_id""",
        {"proposal_id": proposal_id},
    ).fetchone()

    if form.validate_on_submit():
        if not can_vote(current_user["given_name"], proposal):
            flash("Ty tady hlasovat nemůžeš...")
        else:
            db.execute(
                """INSERT INTO event ('proposal_id', 'author_id', 'author_name', 'decision', 'comment', 'created')
                VALUES (:proposal_id, :author_id, :author_name, :decision, :comment, CURRENT_TIMESTAMP)""",
                {
                    "proposal_id": proposal_id,
                    "author_id": current_user["given_name"],
                    "author_name": session["oidc_auth_profile"]['family_name'],
                    "decision": (form.decision.data == "for"),
                    "comment": form.comment.data if bool(form.comment.data) else None,
                },
            )
            db.commit()

        return redirect(f"/proposal/{proposal_id}")

    else:
        if not proposal_exists(proposal_id):
            return redirect("/")

        if not can_vote(current_user["given_name"], proposal):
            flash("Ty tady hlasovat nemůžeš...")
            return redirect("/overview")

        return render_template(
            "voting/vote.html",
            proposal_id=proposal_id,
            form=form,
        )


def proposal_exists(proposal_id: int) -> bool:
    db = get_db()
    return db.execute(
        "SELECT 1 as one FROM proposal WHERE id = :proposal_id",
        {"proposal_id": proposal_id},
    ).fetchone()
