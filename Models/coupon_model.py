from ..extensions import db

class Coupon(db.Model):
    __tablename__ = 'coupon'
    IdCoupon = db.Column(db.Integer, primary_key=True)
    DiscountType = db.Column(db.String(15))
    Value = db.Column(db.Numeric(precision=10, scale=2))
    Code = db.Column(db.String(45))
    TimesRedeemed = db.Column(db.Integer)

    IsValid = db.Column(db.Boolean)
    IdStoreValid = db.Column(db.Integer)
    IdTimeBeginValid = db.Column(db.Integer)
    IdTimeEndValid = db.Column(db.Integer)
    DateBeginValid = db.Column(db.DateTime)
    DateEndValid = db.Column(db.DateTime)

    def to_json(self):
        return {
            'IdCoupon': self.IdRewardMonth,
            'DiscountType': self.StartingDate.strftime("%Y-%m-%d"),
            'Value': self.EndingDate.strftime("%Y-%m-%d"),
            'Code': self.NTimesToReward,
            'TimesRedeemed': self.RewardCategory.to_json(),
            'IsValid': self.RewardCategory.to_json(),
            'IdTimeBeginValid': self.RewardCategory.to_json(),
            'IdTimeEndValid': self.RewardCategory.to_json(),
            'DateBeginValid': self.RewardCategory.to_json(),
            'DateEndValid': self.RewardCategory.to_json(),
        }
        