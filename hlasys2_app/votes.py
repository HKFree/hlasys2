from flask import Blueprint, render_template, redirect, session, request, flash
from hlasys2_app.forms import VoteDecisionForm

bp = Blueprint("votes", __name__)

from hlasys2_app.db import get_db
from hlasys2_app.util import can_vote


@bp.route("/proposal/<int:proposal_id>/vote", methods=["GET", "POST"])
def vote_on_proposal(proposal_id: int):
    db = get_db()
    form: VoteDecisionForm = VoteDecisionForm()

    if form.validate_on_submit():
        if not can_vote(session["user_id"], proposal_id):
            flash("Ty tady hlasovat nemůžeš...")
        else:
            db.execute(
                """INSERT INTO event ('proposal_id', 'user_id', 'decision', 'comment', 'created')
                VALUES (:proposal_id, :user_id, :decision, :comment, CURRENT_TIMESTAMP)""",
                {
                    "proposal_id": proposal_id,
                    "user_id": session["user_id"],
                    "decision": (form.decision.data == "for"),
                    "comment": form.comment.data if bool(form.comment.data) else None,
                },
            )
            db.commit()

        return redirect(f"/proposal/{proposal_id}")

    else:
        if not proposal_exists(proposal_id):
            return redirect("/")

        if not can_vote(session["user_id"], proposal_id):
            flash("Ty tady hlasovat nemůžeš...")
            return redirect("/overview/vv")

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
