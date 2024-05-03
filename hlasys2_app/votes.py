from flask import (
    Blueprint,
    render_template,
    redirect,
    session,
    request
)

bp = Blueprint("votes", __name__)

from hlasys2_app.db import get_db
from hlasys2_app.util import can_vote

@bp.route("/proposal/<int:proposal_id>/vote", methods=['GET', 'POST'])
def vote_on_proposal(proposal_id: int):
    if request.method == 'GET':
        if not proposal_exists(proposal_id):
            return redirect("/")
        
        return render_template(
            "voting/vote.html",
            can_vote=can_vote(session['user_id'], proposal_id),
            proposal_id=proposal_id
        )
    elif request.method == 'POST':
        pass

def proposal_exists(proposal_id: int) -> bool:
    db = get_db()

    return db.execute(
        "SELECT 1 as one FROM proposal WHERE id = :proposal_id",
        {"proposal_id": proposal_id}
    ).fetchone()

