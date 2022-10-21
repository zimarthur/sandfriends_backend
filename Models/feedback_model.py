from ..extensions import db

class Feedback(db.Model):
    __tablename__ = 'feedback'
    IdFeedback = db.Column(db.Integer, primary_key=True)
    Message = db.Column(db.String(255))
    IdUser = db.Column(db.Integer)

    
    def to_json(self):
        return {
            'IdFeedback': self.IdFeedback,
            'Message': self.Message,
            'IdUser': self.IdUser,
        }