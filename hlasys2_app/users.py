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

from hlasys2_app.db import get_db
from hlasys2_app.decorators import login_required

bp = Blueprint("users", __name__)


@bp.route("/user/<int:user_id>")
@login_required
def user_overview(user_id):
    db = get_db()

    user_event = db.execute(
        """SELECT e.* FROM event e
           JOIN proposal p ON p.id = e.proposal_id
           WHERE e.author_id = :user_id AND p.deleted IS NULL
           LIMIT 1""",
        {"user_id": user_id},
    ).fetchone()
    user_proposal = db.execute(
        """SELECT * FROM proposal
           WHERE author_id = :user_id AND deleted IS NULL
           LIMIT 1""",
        {"user_id": user_id},
    ).fetchone()

    if not user_event and not user_proposal:
        flash("Tento uživatel zatím nemá timeline...", "warning")
        return redirect("/overview/vvsopd")

    timeline = db.execute(
        """
        SELECT * FROM (
            SELECT event.author_id AS user_id, event.created, proposal.subject AS events_subject, proposal_id, decision, comment, NULL AS subject, NULL AS proposals_id
            FROM event
            JOIN proposal ON event.proposal_id = proposal.id
            WHERE proposal.deleted IS NULL
            UNION ALL
            SELECT author_id AS user_id, created, NULL AS events_subject, NULL AS proposal_id, NULL AS decision, NULL AS comment, subject, id AS proposals_id
            FROM proposal
            WHERE deleted IS NULL
        )
        WHERE user_id = :user_id
        ORDER BY created DESC""",
        {"user_id": user_id},
    ).fetchall()

    return render_template("user/profile.html", user_event=user_event, timeline=timeline)
