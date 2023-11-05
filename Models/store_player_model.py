from ..extensions import db

class StorePlayer(db.Model):
    __tablename__ = 'store_player'
    IdStorePlayer = db.Column(db.Integer, primary_key=True)
    FirstName = db.Column(db.String(45))
    LastName = db.Column(db.String(45))
    PhoneNumber = db.Column(db.String(45))
    IdStore = db.Column(db.Integer, db.ForeignKey('store.IdStore'))
    IdSport = db.Column(db.Integer, db.ForeignKey('sport.IdSport'))
    IdRankCategory = db.Column(db.Integer, db.ForeignKey('rank_category.IdRankCategory'))
    IdGenderCategory = db.Column(db.Integer, db.ForeignKey('gender_category.IdGenderCategory'))
    Deleted = db.Column(db.Boolean)

    def to_json(self):
        return {
            'IdStorePlayer': self.IdStorePlayer,
            'FirstName': self.FirstName,
            'LastName': self.LastName,
            'PhoneNumber': self.PhoneNumber,
            'IdSport': self.IdSport,
            'IdRankCategory': self.IdRankCategory,
            'IdGenderCategory': self.IdGenderCategory,
        }