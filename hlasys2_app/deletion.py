from datetime import datetime

from flask import (
    Blueprint, flash, redirect, render_template, session, url_for
)

from hlasys2_app.db import get_db
from hlasys2_app.decorators import login_required
from hlasys2_app.forms import DeleteProposalForm
from hlasys2_app.util import HkfreeRole, can_delete_proposal

bp = Blueprint("deletion", __name__)


def _load_deletable_proposal(proposal_id: int, user_id: int):
    """
    Load the proposal and run the pre-delete checks. Mirrors
    votes._load_votable_proposal.

    Returns:
        tuple: (proposal_or_None, redirect_response_or_None)
    """
    db = get_db()
    proposal = db.execute(
        "SELECT * FROM proposal WHERE id = :id", {"id": proposal_id}
    ).fetchone()

    if not proposal:
        flash("Takový návrh neexistuje.", "warning")
        return None, redirect(url_for("proposals.overview"))

    detail = redirect(url_for("proposals.view_proposal", proposal_id=proposal_id))

    if proposal["deleted"] is not None:
        flash("Tento návrh už je smazaný.", "warning")
        return None, detail

    if proposal["decided"] is not None:
        flash("Odhlasovaný návrh nelze smazat.", "danger")
        return None, detail

    if not can_delete_proposal(user_id, proposal):
        flash("Nemáš oprávnění smazat tento návrh.", "danger")
        return None, detail

    return proposal, None


def _count_votes(db, proposal_id: int) -> dict:
    """Latest vote per user, split for/against - drives the confirmation warning."""
    return db.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN e.decision = 1 THEN 1 END), 0) AS votes_for,
            COALESCE(SUM(CASE WHEN e.decision = 0 THEN 1 END), 0) AS votes_against
        FROM event e
        JOIN (
            SELECT author_id, MAX(created) AS max_created
            FROM event
            WHERE proposal_id = :pid AND decision IS NOT NULL
            GROUP BY author_id
        ) latest ON e.author_id = latest.author_id AND e.created = latest.max_created
        WHERE e.proposal_id = :pid AND e.decision IS NOT NULL
        """,
        {"pid": proposal_id},
    ).fetchone()


@bp.route("/proposal/<int:proposal_id>/delete", methods=["GET", "POST"])
@login_required
def delete_proposal(proposal_id: int):
    """Confirmation screen (GET) and the soft delete itself (POST)."""
    user_id = int(session["oidc_auth_profile"]["preferred_username"])
    user_name = session["oidc_auth_profile"]["family_name"]

    proposal, redir = _load_deletable_proposal(proposal_id, user_id)
    if redir is not None:
        return redir

    db = get_db()
    form = DeleteProposalForm()

    if form.validate_on_submit():
        # A single timestamp for both writes. The deletion event is later
        # identified by `event.created = proposal.deleted`, so these two values
        # MUST stay byte-identical. See docs/superpowers/specs.
        ts = datetime.now().isoformat(sep=" ", timespec="microseconds")

        reason = (form.reason.data or "").strip()
        comment = f"Návrh smazal {user_name}."
        if reason:
            comment += f" Důvod: {reason}"

        # The guard lives in the WHERE clause so a double submit cannot produce
        # a second event.
        cursor = db.execute(
            """UPDATE proposal SET deleted = :ts
               WHERE id = :id AND deleted IS NULL AND decided IS NULL""",
            {"ts": ts, "id": proposal_id},
        )
        if cursor.rowcount != 1:
            db.rollback()
            flash("Návrh se mezitím změnil, smazání se neprovedlo.", "warning")
            return redirect(
                url_for("proposals.view_proposal", proposal_id=proposal_id)
            )

        db.execute(
            """INSERT INTO event
                   (proposal_id, author_id, author_name, decision, comment, created)
               VALUES (:pid, :uid, :uname, NULL, :comment, :ts)""",
            {
                "pid": proposal_id,
                "uid": user_id,
                "uname": user_name,
                "comment": comment,
                "ts": ts,
            },
        )
        db.commit()
        flash("Návrh byl smazán.", "success")
        return redirect(url_for("proposals.view_proposal", proposal_id=proposal_id))

    return render_template(
        "proposals/delete.html",
        proposal=proposal,
        form=form,
        votes=_count_votes(db, proposal_id),
        HkfreeRole=HkfreeRole,
    )
