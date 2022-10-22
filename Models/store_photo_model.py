from ..extensions import db

class StorePhoto(db.Model):
    __tablename__ = 'store_photo'
    IdStorePhoto = db.Column(db.Integer, primary_key=True)

    IdStore = db.Column(db.Integer, db.ForeignKey('store.IdStore'))

    def to_json(self):
        return {
            'IdStorePhoto': self.IdStorePhoto,
            'IdStore': self.IdStore,
            'Photo': f"https://www.sandfriends.com.br/img/str/{self.IdStorePhoto}.png",
        }