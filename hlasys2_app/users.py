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

bp = Blueprint("users", __name__)


@bp.route("/user/<int:user_id>")
def user_ovreview(user_id):
    db = get_db()

    user = db.execute(
        "SELECT id, name, email, role FROM user WHERE id = :user_id", {"user_id": user_id}
    ).fetchone()

    if not user:
        flash("User does not exist...")
        return redirect("/overview")

    timeline = db.execute(
        """
        SELECT * FROM (
            SELECT event.user_id AS user_id, event.created, proposal.subject AS events_subject, proposal_id, decision, comment, NULL AS subject, NULL AS proposals_id
            FROM event
            JOIN proposal ON event.proposal_id = proposal.id
            UNION ALL
            SELECT author_id AS user_id, created, NULL AS events_subject, NULL AS proposal_id, NULL AS decision, NULL AS comment, subject, id AS proposals_id
            FROM proposal
        )
        WHERE user_id = :user_id
        ORDER BY created DESC""",
        {"user_id": user_id},
    ).fetchall()

    if user["role"] == 0:
        user["role_str"] = "root"
    elif user["role"] == 1:
        user["role_str"] = "admin"
    else:
        user["role_str"] = "user"

    if not user:
        # flash("No user")
        return redirect("/overview")

    return render_template("user/profile.html", user=user, timeline=timeline)
