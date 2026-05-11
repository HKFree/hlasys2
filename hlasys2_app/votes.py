from flask import Blueprint, render_template, redirect, session, request, flash, url_for
from hlasys2_app.db import get_db
from hlasys2_app.util import check_proposal_status
from hlasys2_app.forms import VoteDecisionForm, QuickVoteForm
from hlasys2_app.decorators import login_required

bp = Blueprint("votes", __name__)


def get_last_vote_details(user_id: int, proposal_id: int) -> dict:
    """
    Fetches the most recent vote event for a user on a proposal.
    Returns the full event row (dict) or None if no vote exists.
    """
    db = get_db()
    last_vote = db.execute(
        """SELECT id, decision, comment, created
           FROM event
           WHERE author_id = :author_id
             AND proposal_id = :proposal_id
             AND decision IS NOT NULL  -- Only actual votes
           ORDER BY created DESC
           LIMIT 1""",
        {"author_id": user_id, "proposal_id": proposal_id},
    ).fetchone()
    return last_vote


def _record_vote(proposal, user_id: int, user_name: str, new_decision: int, provided_comment):
    """
    Shared vote-recording logic. Performs lock check, same-decision early-out,
    change-log auto-comment, INSERT and auto-lock via check_proposal_status.
    Returns a list of (text, category) flash tuples to be emitted by the caller.
    """
    db = get_db()
    last_vote = get_last_vote_details(user_id, proposal["id"])

    if proposal["decided"] and last_vote:
        return [("Návrh je již odhlasován, nelze změnit hlas.", "danger")]

    final_comment = provided_comment.strip() if provided_comment else None
    vote_symbols = ["✖", "✔"]  # 0=against, 1=for

    if last_vote:
        if last_vote["decision"] == new_decision:
            return [("Stejné rozhodnutí, nezapíšu změnu.", "warning")]

        change_desc = (
            f"{user_name} změna hlasu z "
            f"{vote_symbols[last_vote['decision']]} na "
            f"{vote_symbols[new_decision]}"
        )
        final_comment = (
            f"{change_desc} s komentářem:\n{final_comment}"
            if final_comment
            else f"{change_desc}."
        )

    db.execute(
        """INSERT INTO event (proposal_id, author_id, author_name, decision, comment)
           VALUES (:proposal_id, :author_id, :author_name, :decision, :comment)""",
        {
            "proposal_id": proposal["id"],
            "author_id": user_id,
            "author_name": user_name,
            "decision": new_decision,
            "comment": final_comment,
        },
    )
    db.commit()

    flashes = []
    if not proposal["decided"] and check_proposal_status(proposal):
        flashes.append(("Tvůj hlas rozhodnul, návrh byl zamknut", "success"))
    flashes.append(("Hlas zapsán", "success"))
    return flashes


def _load_votable_proposal(proposal_id: int, user_id: int):
    """
    Loads the proposal, runs the shared pre-vote checks (exists, not deleted,
    user is decider). Returns the proposal dict on success, or None if a flash
    + redirect was already emitted - in which case the caller should also redirect.
    Returns a 2-tuple: (proposal_or_None, redirect_response_or_None).
    """
    db = get_db()
    proposal = db.execute(
        "SELECT * FROM proposal WHERE id = :proposal_id",
        {"proposal_id": proposal_id},
    ).fetchone()

    if not proposal:
        flash("Takový návrh neexistuje.", "warning")
        return None, redirect(url_for("proposals.overview"))

    if proposal["deleted"] is not None:
        flash("Tento návrh byl smazán.", "warning")
        return None, redirect(url_for("proposals.overview"))

    if not str(user_id) in proposal["deciders"]:
        flash("Tady hlasovat nemůžeš!", "danger")
        return None, redirect(url_for("proposals.view_proposal", proposal_id=proposal_id))

    return proposal, None


@bp.route("/proposal/<int:proposal_id>/vote", methods=["GET", "POST"])
@login_required
def vote_on_proposal(proposal_id: int):
    current_user_profile = session["oidc_auth_profile"]
    user_id = int(current_user_profile["preferred_username"])
    user_name = current_user_profile["family_name"]

    proposal, redir = _load_votable_proposal(proposal_id, user_id)
    if redir is not None:
        return redir

    form = VoteDecisionForm()

    if request.method == "POST" and form.validate_on_submit():
        new_decision = 1 if form.decision.data == "for" else 0
        for text, cat in _record_vote(proposal, user_id, user_name, new_decision, form.comment.data):
            flash(text, cat)
        return redirect(url_for("proposals.view_proposal", proposal_id=proposal_id))

    # Pre-fill radio with last vote on GET
    last_vote_for_get = (
        get_last_vote_details(user_id, proposal_id) if request.method == "GET" else None
    )
    if last_vote_for_get:
        form.decision.data = "for" if last_vote_for_get["decision"] == 1 else "against"

    return render_template(
        "voting/vote.html",
        proposal=proposal,
        form=form,
        last_vote=last_vote_for_get,
    )


@bp.route("/proposal/<int:proposal_id>/quick-vote", methods=["POST"])
@login_required
def quick_vote(proposal_id: int):
    """One-click PRO/PROTI vote without comment screen."""
    current_user_profile = session["oidc_auth_profile"]
    user_id = int(current_user_profile["preferred_username"])
    user_name = current_user_profile["family_name"]

    proposal, redir = _load_votable_proposal(proposal_id, user_id)
    if redir is not None:
        return redir

    form = QuickVoteForm()
    if not form.validate_on_submit():
        flash("Neplatný požadavek.", "danger")
        return redirect(url_for("proposals.view_proposal", proposal_id=proposal_id))

    new_decision = 1 if form.decision.data == "for" else 0
    for text, cat in _record_vote(proposal, user_id, user_name, new_decision, None):
        flash(text, cat)
    return redirect(url_for("proposals.view_proposal", proposal_id=proposal_id))
