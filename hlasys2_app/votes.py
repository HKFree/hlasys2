from flask import Blueprint, render_template, redirect, session, request, flash, url_for
from hlasys2_app.db import get_db
from hlasys2_app.util import check_proposal_status
from hlasys2_app.forms import VoteDecisionForm
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


@bp.route("/proposal/<int:proposal_id>/vote", methods=["GET", "POST"])
@login_required
def vote_on_proposal(proposal_id: int):
    db = get_db()
    # Get user info
    current_user_profile = session["oidc_auth_profile"]
    user_id = int(current_user_profile["given_name"])
    user_name = current_user_profile["family_name"]

    # Fetch proposal
    proposal = db.execute(
        "SELECT * FROM proposal WHERE id = :proposal_id",
        {"proposal_id": proposal_id},
    ).fetchone()

    if not proposal:
        flash("Takový návrh neexistuje.", "warning")
        return redirect(url_for("proposals.overview"))
    
    if not str(user_id) in proposal['deciders']:
        flash("Tady hlasovat nemůžeš!", "danger")
        return redirect(url_for("proposals.view_proposal", proposal_id=proposal_id))

    form = VoteDecisionForm()

    # Handle POST
    # Use request.method check for clarity along with validation
    if request.method == "POST" and form.validate_on_submit():
        # Determine new decision (1 for 'for', 0 for 'against')
        new_decision = 1 if form.decision.data == "for" else 0
        provided_comment = form.comment.data.strip() if form.comment.data else None

        # Check for existing vote using the helper function (one query)
        last_vote = get_last_vote_details(user_id, proposal_id)

        # Disallow changing vote if proposal was already decided and user already voted
        if proposal['decided'] and last_vote:
            flash("Návrh je již odhlasován, nelze změnit hlas.", "danger")
            return redirect(url_for("proposals.view_proposal", proposal_id=proposal_id))

        final_comment = provided_comment  # Default comment is the one provided
        vote_symbols = ["✖", "✔"]  # Index 0: Against, Index 1: For

        if last_vote:
            # Prevent recording vote if decision hasn't actually changed
            if last_vote["decision"] == new_decision:
                flash("Stejné rozhodnutí, nezapíšu změnu.", "warning")
                return redirect(
                    url_for("proposals.view_proposal", proposal_id=proposal_id)
                )

            # Construct the automatic change comment *before* user comment
            change_desc = (
                f"{user_name} změna hlasu z "
                f"{vote_symbols[last_vote['decision']]} na "
                f"{vote_symbols[new_decision]}"
            )

            # Combine automatic comment and user comment if provided
            final_comment = (
                f"{change_desc} s komentářem:\n{provided_comment}"
                if provided_comment
                else f"{change_desc}."
            )

        # Insert the single event record
        db.execute(
            """INSERT INTO event (proposal_id, author_id, author_name, decision, comment)
               VALUES (:proposal_id, :author_id, :author_name, :decision, :comment)""",
            {
                "proposal_id": proposal_id,
                "author_id": user_id,
                "author_name": user_name,
                "decision": new_decision,
                "comment": final_comment,  # Use the potentially combined comment
            },
        )
        db.commit()

        if not proposal['decided'] and check_proposal_status(proposal):
            flash("Tvůj hlas rozhodnul, návrh byl zamknut", "success")

        flash("Hlas zapsán", "success")
        return redirect(url_for("proposals.view_proposal", proposal_id=proposal_id))

    # Handle GET request (or failed POST validation)
    # Permission already checked, just render the form
    # Optionally, pre-fill form based on last vote for GET request
    last_vote_for_get = (
        get_last_vote_details(user_id, proposal_id) if request.method == "GET" else None
    )
    if last_vote_for_get:
        # Pre-fill form fields if desired (requires WTForms setup)
        form.decision.data = "for" if last_vote_for_get["decision"] == 1 else "against"

    return render_template(
        "voting/vote.html",
        proposal=proposal,  # Pass the whole proposal object
        form=form,
        last_vote=last_vote_for_get,  # Pass last vote details to template if needed
    )
