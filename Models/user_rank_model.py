from ..extensions import db

class UserRank(db.Model):
    __tablename__ = 'user_rank'
    IdUserRank = db.Column(db.Integer, primary_key=True)
    IdUser = db.Column(db.Integer)
    IdRankCategory = db.Column(db.Integer)

    def to_json(self):
        return {
            'IdUserRank': self.IdUserRank,
            'IdUser': self.IdUser,
            'IdRankCategory': self.IdRankCategory,
        }