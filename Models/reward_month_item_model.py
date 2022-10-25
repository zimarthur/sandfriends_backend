from ..extensions import db

class RewardMonthItem(db.Model):
    __tablename__ = 'reward_month_item'
    IdRewardMonthItem = db.Column(db.Integer, primary_key=True)

    IdRewardMonth = db.Column(db.Integer, db.ForeignKey('reward_month.IdRewardMonth'))

    IdRewardItem = db.Column(db.Integer, db.ForeignKey('reward_item.IdRewardItem'))
    RewardItem = db.relationship('RewardItem', foreign_keys = [IdRewardItem])

    def to_json(self):
        return {
            'IdRewardMonthItem': self.IdRewardMonthItem,
            'RewardItem': self.RewardItem.to_json(),
        }
        