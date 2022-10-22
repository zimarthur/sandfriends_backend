from ..extensions import db

class RankCategory(db.Model):
    __tablename__ = 'rank_category'
    IdRankCategory = db.Column(db.Integer, primary_key=True)

    IdSport = db.Column(db.Integer, db.ForeignKey('sport.IdSport'))
    Sport = db.relationship('Sport', foreign_keys = [IdSport])


    RankSportLevel = db.Column(db.Integer)
    RankName = db.Column(db.String(50))
    RankColor = db.Column(db.String(10))

    def to_json(self):
        return {
            'IdRankCategory': self.IdRankCategory,
            'IdSport': self.IdSport,
            'RankSportLevel': self.RankSportLevel,
            'RankName': self.RankName,
            'RankColor': self.RankColor,
        }