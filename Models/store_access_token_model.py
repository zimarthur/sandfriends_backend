from ..extensions import db

class StoreAccessToken(db.Model):
    __tablename__ = 'store_access_token'
    IdStoreAccessToken = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)

    IdStore = db.Column(db.Integer, db.ForeignKey('store.IdStore'))
    Store = db.relationship('Store', foreign_keys = [IdStore])

    AccessToken = db.Column(db.String(225), nullable=False)
    CreationDate = db.Column(db.DateTime, nullable=False)
    LastAccessDate = db.Column(db.DateTime, nullable=False)
   
    def to_json(self):
        return {
            'IdStoreAccessToken': self.IdStoreAccessToken,
            'IdStore': self.IdStore,
            'AccessToken': self.AccessToken,
            'CreationDate': self.CreationDate,
            'LastAccessDate': self.LastAccessDate,
        }