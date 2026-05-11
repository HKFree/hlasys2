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
    comment = TextAreaField("komentář (nepovinný)", name="comment")


class QuickVoteForm(FlaskForm):
    decision = RadioField(
        choices=[("for", "PRO"), ("against", "PROTI")],
        validators=[DataRequired()],
    )


class CreateProposalForm(FlaskForm):
    subject = StringField("Předmět", name="subject", validators=[DataRequired()])
    cost = IntegerField("Odhad ceny", validators=[InputRequired(), NumberRange(min=0)])
    description = TextAreaField("Popis a odůvodnění", name="description", validators=[DataRequired()], render_kw={"rows": 10, "cols": 50, "placeholder": "Co, proč, kam, co to přinese..."})
    type = RadioField(
        "Kdo schvaluje?",
        name="type",
        choices=[(0, "Výkonný Výbor spolku"), (2, "Představenstvo družstva"), (3, "Členové spolku")],
        #choices=[(0, "Výkonný Výbor spolku"), (2, "Představenstvo družstva"), (3, "Členové spolku"), (4, "Družstevníci (členové družstva)")],
        validators=[DataRequired()]
    )
    acceptance = RadioField(
        "Kvorum pro schválení",
        name="acceptance",
        choices=[(0, "více než ½ hlasů"), (1, "více než ⅔ hlasů")],
        validators=[DataRequired()],
        default=1
    )

class CreateCommentForm(FlaskForm):
    comment = TextAreaField("komentář", name="comment", validators=[DataRequired()])
