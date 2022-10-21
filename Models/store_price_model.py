from ..extensions import db

class StorePrice(db.Model):
    __tablename__ = 'store_price'
    IdStorePrice = db.Column(db.Integer, primary_key=True)
    IdStore = db.Column(db.Integer, nullable=False)
    IdStoreCourt = db.Column(db.Integer, nullable=False)
    Weekday = db.Column(db.Integer, nullable=False)
    Hour = db.Column(db.Integer, nullable=False)
    Price = db.Column(db.Numeric, nullable=False)

    def to_json(self):
        return {
            'IdStorePrice': self.IdStorePrice,
            'IdStore': self.IdStore,
            'IdStoreCourt':self.IdStoreCourt,
            'Day': self.Weekday,
            'Hour': self.Hour,
            'Price': self.Price,
        }