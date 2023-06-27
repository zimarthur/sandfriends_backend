from ..extensions import db

class RewardUser(db.Model):
    __tablename__ = 'reward_user'
    IdRewardUser = db.Column(db.Integer, primary_key=True)
    RewardClaimCode = db.Column(db.String(6))
    RewardClaimed = db.Column(db.Boolean)
    RewardClaimedDate = db.Column(db.DateTime)

    IdUser = db.Column(db.Integer, db.ForeignKey('user.IdUser'))
    User = db.relationship('User', foreign_keys = [IdUser])

    IdStore = db.Column(db.Integer, db.ForeignKey('store.IdStore'))
    Store = db.relationship('Store', foreign_keys = [IdStore])

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

        if self.IdStore == None:
            store = None
        else:
            store = self.Store.to_json()

        return {
            'IdRewardUser': self.IdRewardUser,
            'RewardClaimed': self.RewardClaimed,
            'RewardClaimCode': self.RewardClaimCode,
            'User': self.User.to_json(),
            'RewardMonth': self.RewardMonth.to_json(),
            'RewardItem': rewardItem,
            'RewardClaimedDate': rewardClaimedDate,
            'Store':store,
        }
    
    def to_json_store(self):
        return {
            'IdRewardUser': self.IdRewardUser,
            'User': self.User.identification_to_json(),
            'RewardItem': self.RewardItem.to_json(),
            'RewardClaimedDate': self.RewardClaimedDate.strftime("%d/%m/%Y %H:%M"),
        }
        