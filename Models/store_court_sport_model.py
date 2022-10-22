from ..extensions import db

class StoreCourtSport(db.Model):
    __tablename__ = 'store_court_sport'
    IdStoreCourtSport = db.Column(db.Integer, primary_key=True)

    IdStoreCourt = db.Column(db.Integer, db.ForeignKey('store_court.IdStoreCourt'))

    IdSport = db.Column(db.Integer, db.ForeignKey('sport.IdSport'))
    Sport = db.relationship('Sport', foreign_keys = [IdSport])

    def to_json(self):
        return {
            'IdStoreCourtSport': self.IdStoreCourtSport,
            'IdStoreCourt': self.IdStoreCourt,
            'IdSport':self.IdSport,
        }