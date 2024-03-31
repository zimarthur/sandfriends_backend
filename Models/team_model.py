from ..extensions import db

class Team(db.Model):
    __tablename__ = 'team'
    IdTeam = db.Column(db.Integer, primary_key=True)

    IdUser = db.Column(db.Integer, db.ForeignKey('user.IdUser'))
    User = db.relationship('User', foreign_keys = [IdUser])

    Name = db.Column(db.String(45))
    Description = db.Column(db.String(255))
    CreationDate = db.Column(db.DateTime)

    IdSport = db.Column(db.Integer, db.ForeignKey('sport.IdSport'))
    Sport = db.relationship('Sport', foreign_keys = [IdSport])

    IdGenderCategory = db.Column(db.Integer, db.ForeignKey('gender_category.IdGenderCategory'))
    GenderCategory = db.relationship('GenderCategory', foreign_keys = [IdGenderCategory])

    IdRankCategory = db.Column(db.Integer, db.ForeignKey('rank_category.IdRankCategory'))
    RankCategory = db.relationship('RankCategory', foreign_keys = [IdRankCategory])

    def to_json(self):
        return {
            'IdTeam': self.IdTeam,
            'User': self.User.to_json(),
            'Name': self.Name,
            'Description': self.Description,
            'CreationDate': self.CreationDate.strftime("%d/%m/%Y"),
            'IdSport': self.IdSport,
            'IdGenderCategory': self.IdGenderCategory,
            'IdRankCategory': self.IdRankCategory,
        }