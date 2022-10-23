from ..extensions import db

class City(db.Model):
    __tablename__ = 'city'
    IdCity = db.Column(db.Integer, primary_key=True)
    City = db.Column(db.String(255))

    IdState = db.Column(db.Integer, db.ForeignKey('state.IdState'))

    
    def to_json(self):
        return {
            'IdCity': self.IdCity,
            'City': self.City,
            'State': self.State.to_json(),
        }