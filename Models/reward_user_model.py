from ..extensions import db

class RewardUser(db.Model):
    __tablename__ = 'reward_user'
    IdRewardUser = db.Column(db.Integer, primary_key=True)
    RewardClaimed = db.Column(db.Boolean)
    RewardClaimedDate = db.Column(db.DateTime)

    IdUser = db.Column(db.Integer, db.ForeignKey('user.IdUser'))
    User = db.relationship('User', foreign_keys = [IdUser])

    IdRewardMonth = db.Column(db.Integer, db.ForeignKey('reward_month.IdRewardMonth'))
    RewardMonth = db.relationship('RewardMonth', foreign_keys = [IdRewardMonth])

    IdRewardItem = db.Column(db.Integer, db.ForeignKey('reward_item.IdRewardItem'))
    RewardItem = db.relationship('RewardItem', foreign_keys = [IdRewardItem])

    def to_json(self):
        if self.RewardItem == None:
            rewardItem = None
        else:
            rewardItem = self.RewardItem.to_json()
        
        if self.RewardClaimedDate == None:
            rewardClaimedDate = None
        else:
            rewardClaimedDate = self.RewardClaimedDate.strftime("%Y-%m-%d")

        return {
            'IdRewardUser': self.IdRewardUser,
            'RewardClaimed': self.RewardClaimed,
            'User': self.User.to_json(),
            'RewardMonth': self.RewardMonth.to_json(),
            'RewardItem': rewardItem,
            'RewardClaimedDate': rewardClaimedDate,
        }
        