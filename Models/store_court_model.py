from ..extensions import db

class StoreCourt(db.Model):
    __tablename__ = 'store_court'
    IdStoreCourt = db.Column(db.Integer, primary_key=True)
    Description = db.Column(db.String(100))
    IsIndoor = db.Column(db.Boolean)
    IdStore = db.Column(db.Integer, db.ForeignKey('store.IdStore'))

    Prices = db.relationship('StorePrice', backref="StoreCourt")
    Sports = db.relationship('StoreCourtSport', backref="StoreCourt")

    def to_json(self):
        return {
            'IdStoreCourt': self.IdStoreCourt,
            'IdStore': self.IdStore,
            'Description':self.Description,
            'IsIndoor': self.IsIndoor,
        }