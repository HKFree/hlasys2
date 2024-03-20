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
        "SELECT * FROM user WHERE id = :user_id",
        {"user_id": user_id}
    ).fetchone()

    timeline = db.execute("""
        SELECT user_id, created, proposal_id, decision, comment, NULL AS subject, NULL AS proposal_id
        FROM event
        UNION ALL
        SELECT author_id AS user_id, created, NULL AS proposal_id, NULL AS decision, NULL AS comment, subject, id AS proposal_id
        FROM proposal
        WHERE user_id = :user_id
        ORDER BY created DESC""",
        {"user_id": user_id}
    ).fetchall()

    if not user:
        # user neni
        return redirect("/overview")

    # print(timeline)
    return timeline