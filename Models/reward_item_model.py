from ..extensions import db

class RewardItem(db.Model):
    __tablename__ = 'reward_item'
    IdRewardItem = db.Column(db.Integer, primary_key=True)
    Description = db.Column(db.String(255))

    def to_json(self):
        return {
            'IdRewardItem': self.IdRewardItem,
            'Description': self.Description,
        }