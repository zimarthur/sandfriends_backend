from ..extensions import db

class Coupon(db.Model):
    __tablename__ = 'coupon'
    IdCoupon = db.Column(db.Integer, primary_key=True)
    DiscountType = db.Column(db.String(15))
    Value = db.Column(db.Numeric(precision=10, scale=2))
    Code = db.Column(db.String(45))

    IsValid = db.Column(db.Boolean)

    IdStoreValid = db.Column(db.Integer, db.ForeignKey('store.IdStore'))
    StoreValid = db.relationship('Store', foreign_keys = [IdStoreValid])

    IdTimeBeginValid = db.Column(db.Integer)
    IdTimeEndValid = db.Column(db.Integer)
    DateCreated = db.Column(db.DateTime)
    DateBeginValid = db.Column(db.DateTime)
    DateEndValid = db.Column(db.DateTime)

    IsUniqueUse = db.Column(db.Boolean)

    Matches = db.relationship('Match', back_populates="Coupon")

    def to_json(self):
        profit = 0
        for match in self.Matches:
            profit += match.CostUser
        return {
            'IdCoupon': self.IdCoupon,
            'DiscountType': self.DiscountType,
            'Value': self.Value,
            'Code': self.Code,
            'IsValid': self.IsValid,
            'IdTimeBeginValid': self.IdTimeBeginValid,
            'IdTimeEndValid': self.IdTimeEndValid,
            'DateCreated': self.DateCreated.strftime("%d/%m/%Y"),
            'DateBeginValid': self.DateBeginValid.strftime("%d/%m/%Y"),
            'DateEndValid': self.DateEndValid.strftime("%d/%m/%Y"),
            'TimesUsed': len(self.Matches),
            'Profit': profit,
        }

    def to_json_min(self):
        return {
            'IdCoupon': self.IdCoupon,
            'DiscountType': self.DiscountType,
            'Value': self.Value,
            'Code': self.Code,
        }  