from ..extensions import db

class UserRank(db.Model):
    __tablename__ = 'user_rank'
    IdUserRank = db.Column(db.Integer, primary_key=True)

    IdUser = db.Column(db.Integer, db.ForeignKey('user.IdUser'))

    IdRankCategory = db.Column(db.Integer, db.ForeignKey('rank_category.IdRankCategory'))
    RankCategory = db.relationship('RankCategory', foreign_keys = [IdRankCategory])

    def to_json(self):
        return {
            'IdUserRank': self.IdUserRank,
            'IdUser': self.IdUser,
            'RankCategory': self.RankCategory.to_json(),
        }