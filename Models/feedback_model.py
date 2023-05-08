from ..extensions import db

class Feedback(db.Model):
    __tablename__ = 'feedback'
    IdFeedback = db.Column(db.Integer, primary_key=True)
    Feedback = db.Column(db.String(255))
    RegistrationDate = db.Column(db.DateTime)

    IdUser = db.Column(db.Integer, db.ForeignKey('user.IdUser'))
    User = db.relationship('User', foreign_keys = [IdUser])

    def to_json(self):
        return {
            'IdFeedback': self.IdFeedback,
            'Message': self.Message,
            'IdUser': self.IdUser,
        }