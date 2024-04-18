from ..extensions import db

class StorePrice(db.Model):
    __tablename__ = 'store_price'
    IdStorePrice = db.Column(db.Integer, primary_key=True)
    Weekday = db.Column(db.Integer, nullable=False)
    Price = db.Column(db.Numeric, nullable=False)
    RecurrentPrice = db.Column(db.Integer)
    PriceTeacher = db.Column(db.Numeric, nullable=False)
    RecurrentPriceTeacher = db.Column(db.Integer)

    IdAvailableHour = db.Column(db.Integer, db.ForeignKey('available_hour.IdAvailableHour'))
    AvailableHour = db.relationship('AvailableHour', foreign_keys = [IdAvailableHour])

    IdStoreCourt = db.Column(db.Integer, db.ForeignKey('store_court.IdStoreCourt'))


    def to_json(self):
        return {
            'IdStorePrice': self.IdStorePrice,
            'IdStoreCourt':self.IdStoreCourt,
            'Day': self.Weekday,
            'IdAvailableHour': self.IdAvailableHour,
            'Price': self.Price,
            'RecurrentPrice':self.RecurrentPrice,
            'PriceTeacher': self.PriceTeacher,
            'RecurrentPriceTeacher':self.RecurrentPriceTeacher,
        }

    def to_json_recurrentUser(self):
        return {
            'IdAvailableHour': self.IdAvailableHour,
            'Price': self.RecurrentPrice,
        }
    def to_json_recurrentTeacher(self):
        return {
            'IdAvailableHour': self.IdAvailableHour,
            'Price': self.RecurrentPriceTeacher,
        }