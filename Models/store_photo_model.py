from ..extensions import db

class StorePhoto(db.Model):
    __tablename__ = 'store_photo'
    IdStorePhoto = db.Column(db.Integer, primary_key=True)
    Deleted = db.Column(db.Boolean)
    IdStore = db.Column(db.Integer, db.ForeignKey('store.IdStore'))

    def to_json(self):
        return {
            'IdStorePhoto': self.IdStorePhoto,
            'IdStore': self.IdStore,
            'Photo': f"/img/str/{self.IdStorePhoto}.png",
        }