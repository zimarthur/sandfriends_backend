from ..extensions import db

class State(db.Model):
    __tablename__ = 'state'
    IdState = db.Column(db.Integer, primary_key=True)
    State = db.Column(db.String(255))
    UF = db.Column(db.String(5))

    Cities = db.relationship("City", backref="State")
    
    def to_json(self):
        return {
            'IdState': self.IdState,
            'State': self.State,
            'UF': self.UF,
        }
    def to_jsonWithCities(self):
        return {
            'IdState': self.IdState,
            'State': self.State,
            'UF': self.UF,
            'Cities': [city.to_jsonShort() for city in self.Cities],
        }

    def to_jsonWithFilteredCities(self, cityIds):
        return {
            'IdState': self.IdState,
            'State': self.State,
            'UF': self.UF,
            'Cities': [city.to_jsonShort() for city in self.Cities if city.IdCity in cityIds],
        }