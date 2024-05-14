from flask_wtf import FlaskForm
from wtforms import StringField, RadioField, TextAreaField, IntegerField
from wtforms.validators import DataRequired, Length


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
    price = IntegerField("cena")