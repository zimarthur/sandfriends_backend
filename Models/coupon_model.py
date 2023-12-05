from ..extensions import db

class Coupon(db.Model):
    __tablename__ = 'coupon'
    IdCoupon = db.Column(db.Integer, primary_key=True)
    DiscountType = db.Column(db.String(15))
    Value = db.Column(db.Numeric(precision=10, scale=2))
    Code = db.Column(db.String(45))

    IsValid = db.Column(db.Boolean)

    IdStoreValid = db.Column(db.Integer, db.ForeignKey('store.IdStore'))

    IdTimeBeginValid = db.Column(db.Integer)
    IdTimeEndValid = db.Column(db.Integer)
    DateBeginValid = db.Column(db.DateTime)
    DateEndValid = db.Column(db.DateTime)

    def to_json(self):
        return {
            'IdCoupon': self.IdCoupon,
            'DiscountType': self.DiscountType,
            'Value': self.Value,
            'Code': self.Code,
            'IsValid': self.IsValid,
            'IdStoreValid': self.IdStoreValid,
            'IdTimeBeginValid': self.IdTimeBeginValid,
            'IdTimeEndValid': self.IdTimeEndValid,
            'DateBeginValid': self.DateBeginValid.strftime("%Y-%m-%d"),
            'DateEndValid': self.DateEndValid.strftime("%Y-%m-%d"),
        }

    def to_json_min(self):
        return {
            'IdCoupon': self.IdCoupon,
            'DiscountType': self.DiscountType,
            'Value': self.Value,
            'Code': self.Code,
        }  