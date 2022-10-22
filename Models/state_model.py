from ..extensions import db

class State(db.Model):
    __tablename__ = 'state'
    IdState = db.Column(db.Integer, primary_key=True)
    State = db.Column(db.String(255))
    UF = db.Column(db.String(5))

    cities = db.relationship("City", backref="State")
    
    def to_json(self):
        return {
            'IdState': self.IdState,
            'State': self.State,
            'UF': self.UF,
        }