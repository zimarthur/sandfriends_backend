from ..extensions import db

class RewardCategory(db.Model):
    __tablename__ = 'reward_category'
    IdRewardCategory = db.Column(db.Integer, primary_key=True)
    Description = db.Column(db.String(255))

    def to_json(self):
        return {
            'IdRewardCategory': self.IdRewardCategory,
            'Description': self.Description,
        }