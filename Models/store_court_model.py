from ..extensions import db

class StoreCourt(db.Model):
    __tablename__ = 'store_court'
    IdStoreCourt = db.Column(db.Integer, primary_key=True)
    Description = db.Column(db.String(100))
    IsIndoor = db.Column(db.Boolean)
    IdStore = db.Column(db.Integer, db.ForeignKey('store.IdStore'))

    Prices = db.relationship('StorePrice', backref="StoreCourt")
    Sports = db.relationship('StoreCourtSport', backref="StoreCourt")

    def to_json(self):
        return {
            'IdStoreCourt': self.IdStoreCourt,
            'Description':self.Description,
            'IsIndoor': self.IsIndoor,
        }

    #ainda definir, mas a principio mas existem duas necessidades difrerentes: pegar um store json e a suas quadras ou 
    #pegar uma quadra especifica e nela passar o store json, por isso to_jsons diferentes 
    def to_json_match(self): 
        return {
            'IdStoreCourt': self.IdStoreCourt,
            'Description':self.Description,
            'IsIndoor': self.IsIndoor,
            'Store': self.Store.to_json_match(),
        }

    def to_json_full(self): #usado para site (gestor)
        return {
            'IdStoreCourt': self.IdStoreCourt,
            'Store': self.Store.to_json(),
            'Description':self.Description,
            'IsIndoor': self.IsIndoor,
            'Prices' : [price.to_json() for price in self.Prices],
            'Sports' : [sport.to_json() for sport in self.Sports],
        }