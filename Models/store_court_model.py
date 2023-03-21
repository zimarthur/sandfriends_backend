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
            'Store': self.Store.to_json(),
            'Description':self.Description,
            'IsIndoor': self.IsIndoor,
        }

    def to_json_full(self):
        return {
            'IdStoreCourt': self.IdStoreCourt,
            'Store': self.Store.to_json(),
            'Description':self.Description,
            'IsIndoor': self.IsIndoor,
            'Prices' : [price.to_json() for price in self.Prices],
            'Sports' : [sport.to_json() for sport in self.Sports],
        }