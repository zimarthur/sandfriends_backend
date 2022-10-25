from ..extensions import db

class RewardMonth(db.Model):
    __tablename__ = 'reward_month'
    IdRewardMonth = db.Column(db.Integer, primary_key=True)
    StartingDate = db.Column(db.DateTime)
    EndingDate = db.Column(db.DateTime)
    NTimesToReward = db.Column(db.Integer)

    IdRewardCategory = db.Column(db.Integer, db.ForeignKey('reward_category.IdRewardCategory'))
    RewardCategory = db.relationship('RewardCategory', foreign_keys = [IdRewardCategory])

    Rewards = db.relationship('RewardMonthItem', backref="RewardMonth")

    def to_json(self):
        return {
            'IdRewardMonth': self.IdRewardMonth,
            'StartingDate': self.StartingDate.strftime("%Y-%m-%d"),
            'EndingDate': self.EndingDate.strftime("%Y-%m-%d"),
            'NTimesToReward': self.NTimesToReward,
            'RewardCategory': self.RewardCategory.to_json(),
            'Rewards': [reward.to_json() for reward in self.Rewards]
        }
        