from flask_wtf import FlaskForm
from wtforms import StringField, RadioField, TextAreaField, IntegerField
from wtforms.validators import DataRequired, Length, NumberRange, InputRequired


class VoteDecisionForm(FlaskForm):
    decision = RadioField(
        "rozhodnutí",
        name="decision",
        choices=[("for", "✔ jsem PRO"), ("against", "✖ jsem PROTI")],
        validators=[DataRequired()],
    )
    comment = TextAreaField("komentář", name="comment")


class CreateProposalForm(FlaskForm):
    subject = StringField("předmět", name="subject", validators=[DataRequired()])
    cost = IntegerField("cena", validators=[InputRequired(), NumberRange(min=0)])
    description = TextAreaField("popis", name="description", validators=[DataRequired()], render_kw={"rows": 10, "cols": 50})
    type = RadioField(
        "schvaluje",
        name="type",
        choices=[(0, "Výkonný Výbor spolku"), (2, "Představenstvo družstva"), (3, "Členové spolku"), (4, "Členové družstva")],
        validators=[DataRequired()]
    )

class CreateCommentForm(FlaskForm):
    comment = TextAreaField("komentář", name="comment", validators=[DataRequired()])