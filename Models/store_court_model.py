from ..extensions import db

class StoreCourt(db.Model):
    __tablename__ = 'store_court'
    IdStoreCourt = db.Column(db.Integer, primary_key=True)
    IdStore = db.Column(db.Integer, nullable=False)
    Description = db.Column(db.String(100), nullable=False)
    IsIndoor = db.Column(db.Boolean, nullable=False)

    def to_json(self):
        return {
            'IdStoreCourt': self.IdStoreCourt,
            'IdStore': self.IdStore,
            'Description':self.Description,
            'IsIndoor': self.IsIndoor,
        }